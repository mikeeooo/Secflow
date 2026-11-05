"""Dataset loading and validation.

`load_dataset` reads runtime files only. Evaluation labels and split assignments have
separate loaders that only offline training/evaluation code calls; the runtime service
never imports them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from storage.generator import FRAUD_CATEGORIES, RUNTIME_FILES, DatasetSpec, request_fingerprint, sha256_file
from storage.records import (
    Account,
    AuthEvent,
    Counterparty,
    PaymentEvent,
    PaymentRequest,
    auth_from_row,
    parse_ts,
    payment_from_row,
    request_from_row,
)


class DatasetError(RuntimeError):
    """Raised when dataset files are missing, corrupted, or inconsistent."""


@dataclass(frozen=True)
class Dataset:
    path: Path
    manifest: dict[str, Any]
    accounts: dict[str, Account]
    counterparties: dict[str, Counterparty]
    requests: tuple[PaymentRequest, ...]
    payment_events: tuple[PaymentEvent, ...]
    auth_events: tuple[AuthEvent, ...]
    security_events: tuple[dict[str, Any], ...]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise DatasetError(f"Missing dataset file: {path}")
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read_manifest(path: Path) -> dict[str, Any]:
    manifest_path = path / "manifest.json"
    if not manifest_path.exists():
        raise DatasetError(f"Missing manifest: {manifest_path}. Run `python -m backend.cli generate`.")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def verify_hashes(path: Path, manifest: dict[str, Any], names: tuple[str, ...] | None = None) -> None:
    for name, meta in manifest["files"].items():
        if names is not None and name not in names:
            continue
        actual = sha256_file(path / name)
        if actual != meta["sha256"]:
            raise DatasetError(f"Hash mismatch for {name}: manifest {meta['sha256'][:12]}, file {actual[:12]}")


def load_dataset(path: Path, check_hashes: bool = True) -> Dataset:
    """Load the runtime view of a dataset (no labels, splits, or generator parameters)."""
    manifest = read_manifest(path)
    if check_hashes:
        verify_hashes(path, manifest, RUNTIME_FILES)
    accounts = {
        row["account_id"]: Account(
            row["account_id"], row["display_name"], row["account_type"], row["home_country"], parse_ts(row["created_at"])
        )
        for row in read_jsonl(path / "accounts.jsonl")
    }
    counterparties = {
        row["counterparty_id"]: Counterparty(row["counterparty_id"], row["display_name"], row["kind"], row["category"])
        for row in read_jsonl(path / "counterparties.jsonl")
    }
    return Dataset(
        path=path,
        manifest=manifest,
        accounts=accounts,
        counterparties=counterparties,
        requests=tuple(request_from_row(r) for r in read_jsonl(path / "requests.jsonl")),
        payment_events=tuple(payment_from_row(r) for r in read_jsonl(path / "payment_events.jsonl")),
        auth_events=tuple(auth_from_row(r) for r in read_jsonl(path / "authentication_events.jsonl")),
        security_events=tuple(read_jsonl(path / "security_events.jsonl")),
    )


def load_labels(path: Path) -> dict[str, dict[str, Any]]:
    """Offline-only: ground truth for evaluation. Never called by the runtime service."""
    return {row["request_id"]: row for row in read_jsonl(path / "evaluation_labels.jsonl")}


def load_splits(path: Path) -> dict[str, str]:
    """Offline-only: chronological partition of each request."""
    return {row["request_id"]: row["partition"] for row in read_jsonl(path / "split_assignments.jsonl")}


def validate_dataset(path: Path, spec: DatasetSpec) -> list[str]:
    """Return a list of validation problems (empty when the dataset is valid)."""
    problems: list[str] = []
    manifest = read_manifest(path)
    try:
        verify_hashes(path, manifest)
    except DatasetError as error:
        problems.append(str(error))
    requests = read_jsonl(path / "requests.jsonl")
    labels = read_jsonl(path / "evaluation_labels.jsonl")
    accounts = read_jsonl(path / "accounts.jsonl")
    counterparties = read_jsonl(path / "counterparties.jsonl")
    expected_requests = spec.days * spec.requests_per_day
    if len(requests) != expected_requests:
        problems.append(f"Expected {expected_requests} requests, found {len(requests)}")
    if len(accounts) != 400:
        problems.append(f"Expected 400 accounts, found {len(accounts)}")
    if len({a["display_name"] for a in accounts}) != len(accounts):
        problems.append("Account display names are not unique")
    if len({r["request_id"] for r in requests}) != len(requests):
        problems.append("Request IDs are not unique")
    forbidden = {"is_fraud", "is_anomaly", "scenario", "campaign_id", "partition", "label"}
    if requests and forbidden & set(requests[0]):
        problems.append("Runtime requests contain label fields")
    account_ids = {a["account_id"] for a in accounts}
    party_ids = account_ids | {c["counterparty_id"] for c in counterparties}
    for row in requests:
        if row["sender_id"] not in account_ids or row["recipient_id"] not in party_ids:
            problems.append(f"Dangling reference in {row['request_id']}")
            break
    fraud_total = sum(1 for l in labels if l["is_fraud"])
    per_category = sum(spec.fraud_per_category.values())
    if fraud_total != per_category * len(FRAUD_CATEGORIES):
        problems.append(f"Unexpected fraud total {fraud_total}")
    unusual = sum(1 for l in labels if not l["is_fraud"] and l["scenario"] != "routine_payment")
    if unusual != sum(spec.unusual_per_partition.values()):
        problems.append(f"Unexpected unusual-legitimate total {unusual}")
    if len(spec.partitions) > 1:
        problems += _validate_partitions(path, spec, requests, labels)
    return problems


def _validate_partitions(
    path: Path, spec: DatasetSpec, requests: list[dict[str, Any]], labels: list[dict[str, Any]]
) -> list[str]:
    problems: list[str] = []
    splits = load_splits(path)
    label_by_id = {l["request_id"]: l for l in labels}
    campaign_parts: dict[str, set[str]] = {}
    counts: dict[str, dict[str, int]] = {}
    previous_part_index = 0
    order = [p.name for p in spec.partitions]
    for row in requests:
        part = splits[row["request_id"]]
        index = order.index(part)
        if index < previous_part_index:
            problems.append("Partitions are not chronological")
            break
        previous_part_index = index
        label = label_by_id[row["request_id"]]
        if label["campaign_id"]:
            campaign_parts.setdefault(label["campaign_id"], set()).add(part)
        bucket = counts.setdefault(part, {})
        key = label["scenario"] if label["is_fraud"] else ("routine" if label["scenario"] == "routine_payment" else "unusual")
        bucket[key] = bucket.get(key, 0) + 1
        bucket["total"] = bucket.get("total", 0) + 1
    split_campaigns = [c for c, parts in campaign_parts.items() if len(parts) > 1]
    if split_campaigns:
        problems.append(f"{len(split_campaigns)} campaigns cross partition boundaries")
    for partition in spec.partitions:
        bucket = counts.get(partition.name, {})
        expected_total = (partition.last_day - partition.first_day + 1) * spec.requests_per_day
        if bucket.get("total") != expected_total:
            problems.append(f"{partition.name}: expected {expected_total} requests, found {bucket.get('total')}")
        for category in FRAUD_CATEGORIES:
            if bucket.get(category) != spec.fraud_per_category[partition.name]:
                problems.append(f"{partition.name}: {category} count {bucket.get(category)}")
        if bucket.get("unusual") != spec.unusual_per_partition[partition.name]:
            problems.append(f"{partition.name}: unusual count {bucket.get('unusual')}")
    return problems


def cross_dataset_fingerprint_overlap(first: Path, second: Path) -> int:
    a = {request_fingerprint(r) for r in read_jsonl(first / "requests.jsonl")}
    b = {request_fingerprint(r) for r in read_jsonl(second / "requests.jsonl")}
    return len(a & b)
