"""Read-only analytics for the monitoring dashboard and the DBSCAN cluster graph.

Nothing here refits a model or reads labels. The dashboard aggregates recorded assessments
into time buckets. The cluster graph is built from the frozen DBSCAN core samples saved in
the model bundle, plus the recorded requests whose trailing 24-hour profile fell outside
every core neighbourhood (`outside_context`), linked to their nearest frozen cluster.
"""

from __future__ import annotations

import math
import threading
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
from sklearn.neighbors import NearestNeighbors

from ml.algorithms.dbscan_context import DBSCANContext
from ml.policy import OperatingPoint
from storage.memory import COMPLETED_OUTCOMES, AssessmentRecord
from storage.records import format_ts

WINDOWS = {
    "history": {"bucket_seconds": 86_400, "max_buckets": None, "label": "Demonstration history and session, per day"},
    "live": {"bucket_seconds": 60, "max_buckets": 30, "label": "Simulations, last 30 simulated minutes, per minute"},
}
PERCENTILES = (50, 90, 99)


def _bucket_template(start: int) -> dict[str, Any]:
    return {
        "t": start, "requests": 0, "permit": 0, "verify": 0, "block_risk": 0, "block_evidence": 0,
        "safeguard": 0, "outside_context": 0, "scored": 0, "completed_amount": 0.0, "pending_amount": 0.0,
        "blocked_amount": 0.0, "_if": [], "_lof": [], "_rules": [], "_risk": [], "_latency": [],
    }


def _mean(values: list[float]) -> float | None:
    return round(float(np.mean(values)), 4) if values else None


def dashboard(
    records: Sequence[AssessmentRecord], window: str, now_ts: int, point: OperatingPoint, goals: dict[str, float]
) -> dict[str, Any]:
    spec = WINDOWS[window]
    size = int(spec["bucket_seconds"])
    if window == "live":
        selected = [r for r in records if r.origin == "simulation"]
        # Simulated events can run slightly ahead of the wall-clock simulation time (sign-in steps advance it).
        latest = max([now_ts, *(r.request.ts for r in selected)])
        end = latest - latest % size
        first = end - size * (int(spec["max_buckets"]) - 1)
        selected = [r for r in selected if r.request.ts >= first]
    else:
        selected = list(records)
        first = min((r.request.ts for r in selected), default=now_ts)
        first -= first % size
        end = max((r.request.ts for r in selected), default=now_ts)
        end -= end % size
    buckets = {t: _bucket_template(t) for t in range(first, end + 1, size)}
    rules: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    for r in selected:
        b = buckets.setdefault(r.request.ts - r.request.ts % size, _bucket_template(r.request.ts - r.request.ts % size))
        policy = r.result.policy
        b["requests"] += 1
        sources[policy.decision_source] += 1
        if policy.decision == "Permit":
            b["permit"] += 1
        elif policy.decision == "Verify":
            b["verify"] += 1
            b["safeguard"] += int(policy.decision_source == "assessment_safeguard")
        elif policy.decision_source == "confirmed_fraud_evidence":
            b["block_evidence"] += 1
        else:
            b["block_risk"] += 1
        amount = r.request.amount
        if r.outcome in COMPLETED_OUTCOMES:
            b["completed_amount"] += amount
        elif r.outcome == "pending_verification":
            b["pending_amount"] += amount
        else:
            b["blocked_amount"] += amount
        c = r.result.components
        if c is not None:
            b["scored"] += 1
            b["_if"].append(c.if_score)
            b["_lof"].append(c.lof_score)
            b["outside_context"] += int(c.context.status == "outside_context")
        if r.result.risk is not None:
            b["_risk"].append(r.result.risk.total)
        b["_rules"].append(r.result.rules.score)
        if r.latency_ms is not None:
            b["_latency"].append(r.latency_ms)
        rules.update(t.code for t in r.result.rules.triggered)

    series = []
    for t in sorted(buckets):
        b = buckets[t]
        risk = b.pop("_risk")
        latency = b.pop("_latency")
        row = {
            **{k: v for k, v in b.items() if not k.startswith("_")},
            "t": format_ts(t),
            "mean_isolation_forest": _mean(b.pop("_if")),
            "mean_lof": _mean(b.pop("_lof")),
            "mean_rules": _mean(b.pop("_rules")),
            "latency_mean_ms": _mean(latency),
            "latency_max_ms": round(max(latency), 3) if latency else None,
        }
        for q in PERCENTILES:
            row[f"risk_p{q}"] = round(float(np.percentile(risk, q)), 2) if risk else None
        for key in ("completed_amount", "pending_amount", "blocked_amount"):
            row[key] = round(row[key], 2)
        series.append(row)

    total = len(selected)
    verify = sum(s["verify"] for s in series)
    blocks = sum(s["block_risk"] + s["block_evidence"] for s in series)
    scored = sum(s["scored"] for s in series)
    outside = sum(s["outside_context"] for s in series)
    latencies = sorted(r.latency_ms for r in selected if r.latency_ms is not None)
    return {
        "window": window,
        "label": spec["label"],
        "bucket_seconds": size,
        "range": {"from": format_ts(first), "to": format_ts(end + size)},
        "series": series,
        "totals": {
            "requests": total,
            "verify_rate": verify / total if total else None,
            "block_rate": blocks / total if total else None,
            "outside_context_rate": outside / scored if scored else None,
            "preventive_blocks": sum(s["block_risk"] for s in series),
            "evidence_blocks": sum(s["block_evidence"] for s in series),
            "latency_mean_ms": round(float(np.mean(latencies)), 3) if latencies else None,
            "latency_p95_ms": round(latencies[max(0, math.ceil(len(latencies) * 0.95) - 1)], 3) if latencies else None,
        },
        "decision_sources": dict(sources),
        "rule_triggers": [{"code": code, "count": n, "share": n / total} for code, n in rules.most_common(8)],
        "thresholds": {"verify": point.verify, "block": point.block},
        "goals": {"max_verify_rate": goals.get("max_verify_rate")},
    }


class ClusterGraphBuilder:
    """Builds the static cluster backbone once, then attaches current anomalies on each call."""

    def __init__(self, context: DBSCANContext, members_cap: int = 12, link_factor: float = 2.0, seed: int = 7) -> None:
        self.context = context
        self.members_cap = members_cap
        self.link_factor = link_factor
        self.seed = seed
        self._static: dict[str, Any] | None = None
        self._lock = threading.Lock()

    def _build_static(self) -> dict[str, Any]:
        cores = np.asarray(self.context.core_samples)
        labels = np.asarray(self.context.core_labels)
        eps = self.context.eps
        clusters = sorted(int(c) for c in set(labels.tolist()))
        sizes = {c: int((labels == c).sum()) for c in clusters}
        centroids = {c: cores[labels == c].mean(axis=0) for c in clusters}

        k = min(30, len(cores))
        distances, indices = NearestNeighbors(n_neighbors=k).fit(cores).kneighbors(cores)
        neighbour_labels = labels[indices]
        cross = neighbour_labels != labels[:, None]
        pair_min: dict[tuple[int, int], float] = {}
        pair_count: Counter[tuple[int, int]] = Counter()
        for row, col in zip(*np.nonzero(cross), strict=True):
            a, b = int(labels[row]), int(neighbour_labels[row, col])
            key = (a, b) if a < b else (b, a)
            d = float(distances[row, col])
            pair_count[key] += 1
            if d < pair_min.get(key, math.inf):
                pair_min[key] = d
        edges = [
            {"source": f"c{a}", "target": f"c{b}", "kind": "near", "distance": round(d, 4), "pairs": pair_count[(a, b)]}
            for (a, b), d in pair_min.items()
            if d <= self.link_factor * eps
        ]
        linked = {e["source"] for e in edges} | {e["target"] for e in edges}
        centroid_matrix = np.stack([centroids[c] for c in clusters])
        if len(clusters) > 1:
            dist, idx = NearestNeighbors(n_neighbors=2).fit(centroid_matrix).kneighbors(centroid_matrix)
            for i, c in enumerate(clusters):
                if f"c{c}" in linked:
                    continue
                other = clusters[int(idx[i, 1])]
                edges.append({"source": f"c{c}", "target": f"c{other}", "kind": "nearest", "distance": round(float(dist[i, 1]), 4), "pairs": 0})

        rng = np.random.default_rng(self.seed)
        nodes: list[dict[str, Any]] = []
        for c in clusters:
            nodes.append({"id": f"c{c}", "kind": "cluster", "cluster": c, "size": sizes[c]})
            members = np.flatnonzero(labels == c)
            take = min(len(members), max(2, min(self.members_cap, round(math.sqrt(sizes[c])))))
            for j, core_index in enumerate(np.sort(rng.choice(members, size=take, replace=False))):
                node_id = f"m{c}-{j}"
                distance = float(np.linalg.norm(cores[core_index] - centroids[c]))
                nodes.append({"id": node_id, "kind": "core", "cluster": c})
                edges.append({"source": f"c{c}", "target": node_id, "kind": "member", "distance": round(distance, 4), "pairs": 0})
        return {
            "nodes": nodes,
            "edges": edges,
            "clusters": [{"cluster": c, "size": sizes[c]} for c in sorted(clusters, key=lambda c: -sizes[c])],
            "summary": {
                "clusters": len(clusters),
                "core_samples": len(cores),
                "eps": eps,
                "min_samples": self.context.min_samples,
                "link_distance": round(self.link_factor * eps, 4),
                "near_links": sum(1 for e in edges if e["kind"] == "near"),
                "nearest_links": sum(1 for e in edges if e["kind"] == "nearest"),
                "training_noise_fraction": self.context.summary.get("noise_fraction"),
            },
        }

    def build(self, records: Sequence[AssessmentRecord], party: Callable[[str], Any], max_anomalies: int) -> dict[str, Any]:
        with self._lock:
            if self._static is None:
                self._static = self._build_static()
        static = self._static
        outside = [
            r for r in records
            if r.result.components is not None and r.result.components.context.status == "outside_context"
        ]
        outside.sort(key=lambda r: r.key, reverse=True)
        anomaly_nodes, anomaly_edges = [], []
        per_cluster: defaultdict[int, int] = defaultdict(int)
        for r in outside[:max_anomalies]:
            ctx = r.result.components.context  # type: ignore[union-attr]
            node_id = f"a:{r.request.request_id}"
            anomaly_nodes.append({
                "id": node_id, "kind": "anomaly", "cluster": ctx.nearest_cluster, "request_id": r.request.request_id,
                "decision_label": r.result.policy.label, "risk_score": round(r.result.risk.total, 2) if r.result.risk else None,
                "distance": round(ctx.distance or 0.0, 4), "sender": party(r.request.sender_id).name,
                "recipient": party(r.request.recipient_id).name, "amount": r.request.amount,
                "event_time": format_ts(r.request.ts), "origin": r.origin,
            })
            if ctx.nearest_cluster is not None:
                per_cluster[ctx.nearest_cluster] += 1
                anomaly_edges.append({"source": f"c{ctx.nearest_cluster}", "target": node_id, "kind": "anomaly",
                                      "distance": round(ctx.distance or 0.0, 4), "pairs": 0})
        clusters = [{**c, "anomalies": per_cluster.get(c["cluster"], 0)} for c in static["clusters"]]
        return {
            "nodes": static["nodes"] + anomaly_nodes,
            "edges": static["edges"] + anomaly_edges,
            "clusters": clusters,
            "summary": {
                **static["summary"],
                "anomalies_total": len(outside),
                "anomalies_shown": len(anomaly_nodes),
                "note": "Clusters and core samples come from the frozen training fit. Anomalies are recorded requests "
                "whose trailing 24-hour profile lies outside every core neighbourhood; each links to its nearest "
                "cluster. This is account context, not a fraud verdict.",
            },
        }
