import {
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type Simulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3-force";
import { Maximize2, Minus, Pause, Play, Plus } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";
import type { ClusterGraph as GraphData, DecisionLabel, GraphEdge, GraphNode } from "../api/types";
import { formatMoney } from "../lib/format";
import { DecisionBadge } from "./DecisionBadge";
import { Button, Chip, cx } from "./ui";

type SimNode = GraphNode & SimulationNodeDatum & { r: number; px?: number; py?: number };

const ROTATION_SPEED = 0.08; // radians per second: one full turn in about 80 seconds

function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
type SimLink = SimulationLinkDatum<SimNode> & Pick<GraphEdge, "kind" | "distance" | "pairs">;

/**
 * The network always renders on a dark canvas (in both appearances), like an observatory view:
 * light marks on near-black make dense structure readable. Decision colours use the dark-mode steps.
 */
const GRAPH = {
  background: "#08090c",
  edge: "#8e8e99",
  core: "#c7c7cc",
  hub: "#4da3ff",
  label: "#f5f5f7",
  ring: "#ffffff",
};
const DECISION_COLOR: Record<DecisionLabel, string> = {
  Permitted: "#32d74b",
  "Needs verification": "#ffb340",
  "Preventive risk block": "#ff6961",
  "Confirmed fraud evidence": "#f5f5f7",
};

function radius(node: GraphNode): number {
  if (node.kind === "cluster") return 3 + 1.6 * Math.log(1 + (node.size ?? 1));
  if (node.kind === "anomaly") return 4.5;
  return 1.8;
}

/**
 * Force-directed view of the frozen DBSCAN clusters: hubs sized by core-sample count, a sample of core
 * samples as spokes, links between clusters whose cores lie within twice eps, and anomalous profiles
 * (outside every core neighbourhood) drawn as diamonds linked to their nearest cluster.
 */
export function ClusterGraph({ data, showCores }: { data: GraphData; showCores: boolean }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const simRef = useRef<Simulation<SimNode, SimLink> | null>(null);
  const nodesRef = useRef<SimNode[]>([]);
  const linksRef = useRef<SimLink[]>([]);
  const view = useRef({ k: 1, x: 0, y: 0, cx: 0, cy: 0, auto: true });
  const angleRef = useRef(0);
  const pointerInsideRef = useRef(false);
  const draggingRef = useRef(false);
  const sizeRef = useRef({ w: 800, h: 560 });
  const hoverRef = useRef<SimNode | null>(null);
  const selectedRef = useRef<number | null>(null);
  const showCoresRef = useRef(showCores);
  const [hover, setHover] = useState<{ node: SimNode; x: number; y: number } | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [rotating, setRotating] = useState(() => !prefersReducedMotion());
  const navigate = useNavigate();

  const neighbours = useMemo(() => {
    const map = new Map<number, { cluster: number; distance: number; kind: string }[]>();
    for (const e of data.edges) {
      if (e.kind !== "near" && e.kind !== "nearest") continue;
      const a = Number(e.source.slice(1));
      const b = Number(e.target.slice(1));
      map.set(a, [...(map.get(a) ?? []), { cluster: b, distance: e.distance, kind: e.kind }]);
      map.set(b, [...(map.get(b) ?? []), { cluster: a, distance: e.distance, kind: e.kind }]);
    }
    return map;
  }, [data]);

  const draw = () => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext?.("2d");
    if (!canvas || !ctx) return;
    const { w, h } = sizeRef.current;
    const dpr = window.devicePixelRatio || 1;
    const nodes = nodesRef.current;
    if (view.current.auto && nodes.length) fit(nodes);
    const { k, x, y, cx, cy } = view.current;
    const cos = Math.cos(angleRef.current);
    const sin = Math.sin(angleRef.current);
    for (const n of nodes) {
      const dx = (n.x ?? 0) - cx;
      const dy = (n.y ?? 0) - cy;
      n.px = cx + dx * cos - dy * sin;
      n.py = cy + dx * sin + dy * cos;
    }
    canvas.dataset.view = `${k.toFixed(4)},${x.toFixed(1)},${y.toFixed(1)},${angleRef.current.toFixed(3)}`;
    const focus = selectedRef.current;
    const linked = focus == null ? null : new Set([focus, ...(neighbours.get(focus) ?? []).map((n) => n.cluster)]);
    const dim = (cluster: number | null | undefined) => linked != null && (cluster == null || !linked.has(cluster));

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = GRAPH.background;
    ctx.fillRect(0, 0, w, h);
    ctx.setTransform(dpr * k, 0, 0, dpr * k, dpr * (w / 2 + x), dpr * (h / 2 + y));

    for (const link of linksRef.current) {
      const s = link.source as SimNode;
      const t = link.target as SimNode;
      if (link.kind === "member" && !showCoresRef.current) continue;
      const faded = dim(s.cluster) && dim(t.cluster);
      ctx.globalAlpha = faded ? 0.05 : link.kind === "member" ? 0.3 : link.kind === "anomaly" ? 0.5 : 0.45;
      ctx.lineWidth = (link.kind === "near" ? 0.6 + Math.log1p(link.pairs) * 0.35 : 0.6) / Math.sqrt(k);
      ctx.strokeStyle = link.kind === "anomaly" ? DECISION_COLOR[t.decision_label ?? "Permitted"] : GRAPH.edge;
      ctx.setLineDash(link.kind === "nearest" || link.kind === "anomaly" ? [3 / k, 3 / k] : []);
      ctx.beginPath();
      ctx.moveTo(s.px ?? 0, s.py ?? 0);
      ctx.lineTo(t.px ?? 0, t.py ?? 0);
      ctx.stroke();
    }
    ctx.setLineDash([]);

    for (const node of nodes) {
      if (node.kind === "core" && !showCoresRef.current) continue;
      ctx.globalAlpha = dim(node.cluster) ? 0.12 : 1;
      const nx = node.px ?? 0;
      const ny = node.py ?? 0;
      if (node.kind === "anomaly") {
        const c = DECISION_COLOR[node.decision_label ?? "Permitted"];
        ctx.fillStyle = c;
        ctx.strokeStyle = GRAPH.background;
        ctx.lineWidth = 1.5 / k;
        ctx.beginPath();
        ctx.moveTo(nx, ny - node.r);
        ctx.lineTo(nx + node.r, ny);
        ctx.lineTo(nx, ny + node.r);
        ctx.lineTo(nx - node.r, ny);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
        ctx.globalAlpha *= 0.35;
        ctx.strokeStyle = c;
        ctx.beginPath();
        ctx.arc(nx, ny, node.r + 3, 0, Math.PI * 2);
        ctx.stroke();
      } else {
        ctx.fillStyle = node.kind === "cluster" ? GRAPH.hub : GRAPH.core;
        ctx.beginPath();
        ctx.arc(nx, ny, node.r, 0, Math.PI * 2);
        ctx.fill();
        if (node.kind === "cluster" && node.cluster === focus) {
          ctx.strokeStyle = GRAPH.ring;
          ctx.lineWidth = 2 / k;
          ctx.stroke();
        }
      }
    }
    ctx.globalAlpha = 1;
    ctx.fillStyle = GRAPH.label;
    ctx.font = `${11 / k}px -apple-system, system-ui, sans-serif`;
    for (const node of nodes) {
      if (node.kind === "cluster" && ((node.size ?? 0) > 400 || node.cluster === focus) && !dim(node.cluster)) {
        ctx.fillText(`C${node.cluster}`, (node.px ?? 0) + node.r + 2 / k, (node.py ?? 0) - node.r);
      }
    }
    const hovered = hoverRef.current;
    if (hovered) {
      ctx.strokeStyle = GRAPH.ring;
      ctx.lineWidth = 1.5 / k;
      ctx.beginPath();
      ctx.arc(hovered.px ?? 0, hovered.py ?? 0, hovered.r + 4, 0, Math.PI * 2);
      ctx.stroke();
    }
  };

  /** Fit by the layout's radius around its centroid, so the frame stays still while the graph rotates. */
  function fit(nodes: SimNode[]) {
    const { w, h } = sizeRef.current;
    let sx = 0, sy = 0;
    for (const n of nodes) {
      sx += n.x ?? 0;
      sy += n.y ?? 0;
    }
    const cx = sx / nodes.length;
    const cy = sy / nodes.length;
    let radius = 1;
    for (const n of nodes) radius = Math.max(radius, Math.hypot((n.x ?? 0) - cx, (n.y ?? 0) - cy) + n.r);
    const k = Math.min(4, Math.max(0.05, (Math.min(w, h) - 32) / (2 * radius)));
    view.current = { k, x: -cx * k, y: -cy * k, cx, cy, auto: true };
  }

  // Build the simulation whenever the data changes.
  useEffect(() => {
    const nodes: SimNode[] = data.nodes.map((n) => ({ ...n, r: radius(n) }));
    const links: SimLink[] = data.edges.map((e) => ({ ...e }));
    nodesRef.current = nodes;
    linksRef.current = links;
    const eps = data.summary.eps || 1;
    const sim = forceSimulation<SimNode, SimLink>(nodes)
      .force(
        "link",
        forceLink<SimNode, SimLink>(links)
          .id((d) => d.id)
          .distance((l) => (l.kind === "member" ? 8 + 6 * l.distance : l.kind === "anomaly" ? 18 + 14 * (l.distance / eps) : l.kind === "near" ? 40 + 30 * (l.distance / eps) : 110))
          .strength((l) => (l.kind === "member" ? 0.9 : l.kind === "anomaly" ? 0.5 : l.kind === "near" ? 0.25 : 0.08)),
      )
      .force("charge", forceManyBody<SimNode>().strength((d) => (d.kind === "cluster" ? -30 - 3 * Math.sqrt(d.size ?? 1) : d.kind === "anomaly" ? -10 : -4)).distanceMax(260))
      .force("collide", forceCollide<SimNode>((d) => d.r + 1))
      .force("x", forceX<SimNode>(0).strength(0.07))
      .force("y", forceY<SimNode>(0).strength(0.07))
      .alphaDecay(0.03);
    simRef.current = sim;
    view.current.auto = true;
    if (prefersReducedMotion()) {
      sim.stop();
      sim.tick(300);
      draw();
    } else {
      sim.on("tick", draw);
    }
    return () => {
      sim.stop();
      sim.on("tick", null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  // Keep the canvas sized to its container.
  useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => {
      const w = wrap.clientWidth;
      const h = Math.max(380, Math.min(680, Math.round(w * 0.62)));
      sizeRef.current = { w, h };
      const dpr = window.devicePixelRatio || 1;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      draw();
    });
    observer.observe(wrap);
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    selectedRef.current = selected;
    showCoresRef.current = showCores;
    draw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, showCores]);

  // Slow continuous rotation; holds still while the pointer is over the graph so nodes can be inspected.
  useEffect(() => {
    if (!rotating || typeof requestAnimationFrame === "undefined") return;
    let frame = 0;
    let last = performance.now();
    const step = (now: number) => {
      const dt = Math.min(0.1, (now - last) / 1000);
      last = now;
      if (!pointerInsideRef.current && !draggingRef.current) {
        angleRef.current = (angleRef.current + dt * ROTATION_SPEED) % (Math.PI * 2);
        draw();
      }
      frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rotating]);

  // Pointer interaction: wheel zoom, drag to pan, hover, click.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    let drag: { x: number; y: number; moved: boolean } | null = null;
    const toWorld = (event: { offsetX: number; offsetY: number }) => {
      const { w, h } = sizeRef.current;
      const { k, x, y, cx, cy } = view.current;
      const rx = (event.offsetX - w / 2 - x) / k - cx;
      const ry = (event.offsetY - h / 2 - y) / k - cy;
      const cos = Math.cos(-angleRef.current);
      const sin = Math.sin(-angleRef.current);
      return { wx: cx + rx * cos - ry * sin, wy: cy + rx * sin + ry * cos };
    };
    const find = (event: { offsetX: number; offsetY: number }) => {
      const { wx, wy } = toWorld(event);
      const found = simRef.current?.find(wx, wy, 14 / view.current.k) ?? null;
      return found && (found.kind !== "core" || showCoresRef.current) ? found : null;
    };
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const factor = Math.exp(-event.deltaY * 0.0015);
      zoomAt(event.offsetX, event.offsetY, factor);
    };
    const onDown = (event: PointerEvent) => {
      drag = { x: event.clientX, y: event.clientY, moved: false };
      draggingRef.current = true;
      canvas.setPointerCapture(event.pointerId);
    };
    const onMove = (event: PointerEvent) => {
      if (drag) {
        const dx = event.clientX - drag.x;
        const dy = event.clientY - drag.y;
        if (Math.abs(dx) + Math.abs(dy) > 2) drag.moved = true;
        if (drag.moved) {
          view.current = { ...view.current, x: view.current.x + dx, y: view.current.y + dy, auto: false };
          drag.x = event.clientX;
          drag.y = event.clientY;
          draw();
          return;
        }
      }
      const node = find(event);
      hoverRef.current = node;
      canvas.style.cursor = node ? "pointer" : drag ? "grabbing" : "grab";
      setHover(node ? { node, x: event.offsetX, y: event.offsetY } : null);
      draw();
    };
    const onUp = (event: PointerEvent) => {
      const wasDrag = drag?.moved;
      drag = null;
      draggingRef.current = false;
      if (wasDrag) return;
      const node = find(event);
      if (!node) return setSelected(null);
      if (node.kind === "anomaly" && node.request_id) navigate(`/investigations/${encodeURIComponent(node.request_id)}`);
      else setSelected((current) => (current === node.cluster ? null : node.cluster));
    };
    const onEnter = () => {
      pointerInsideRef.current = true;
    };
    const onLeave = () => {
      pointerInsideRef.current = false;
      hoverRef.current = null;
      setHover(null);
      draw();
    };
    canvas.addEventListener("wheel", onWheel, { passive: false });
    canvas.addEventListener("pointerdown", onDown);
    canvas.addEventListener("pointermove", onMove);
    canvas.addEventListener("pointerup", onUp);
    canvas.addEventListener("pointerleave", onLeave);
    canvas.addEventListener("pointerenter", onEnter);
    return () => {
      canvas.removeEventListener("pointerenter", onEnter);
      canvas.removeEventListener("wheel", onWheel);
      canvas.removeEventListener("pointerdown", onDown);
      canvas.removeEventListener("pointermove", onMove);
      canvas.removeEventListener("pointerup", onUp);
      canvas.removeEventListener("pointerleave", onLeave);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate]);

  function zoomAt(sx: number, sy: number, factor: number) {
    const { w, h } = sizeRef.current;
    const v = view.current;
    const k = Math.min(12, Math.max(0.05, v.k * factor));
    const cx0 = sx - w / 2;
    const cy0 = sy - h / 2;
    view.current = { ...v, k, x: cx0 - ((cx0 - v.x) / v.k) * k, y: cy0 - ((cy0 - v.y) / v.k) * k, auto: false };
    draw();
  }

  const selectedInfo = selected == null ? null : data.clusters.find((c) => c.cluster === selected);
  const selectedAnomalies = selected == null ? [] : data.nodes.filter((n) => n.kind === "anomaly" && n.cluster === selected);

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_300px]">
      <div className="relative min-w-0 overflow-hidden rounded-[10px] bg-[#08090c]" ref={wrapRef}>
        <canvas
          ref={canvasRef}
          role="img"
          aria-label={`Force-directed graph of ${data.summary.clusters} DBSCAN clusters with ${data.summary.near_links} links between nearby clusters and ${data.summary.anomalies_shown} anomalous profiles linked to their nearest cluster. A table version follows.`}
          className="block touch-none"
        />
        <div className="absolute top-3 right-3 flex gap-1">
          <Button aria-label={rotating ? "Pause rotation" : "Rotate graph"} aria-pressed={rotating} onClick={() => setRotating((r) => !r)}>
            {rotating ? <Pause aria-hidden className="size-4" /> : <Play aria-hidden className="size-4" />}
          </Button>
          <Button aria-label="Zoom in" onClick={() => zoomAt(sizeRef.current.w / 2, sizeRef.current.h / 2, 1.4)}><Plus aria-hidden className="size-4" /></Button>
          <Button aria-label="Zoom out" onClick={() => zoomAt(sizeRef.current.w / 2, sizeRef.current.h / 2, 1 / 1.4)}><Minus aria-hidden className="size-4" /></Button>
          <Button aria-label="Fit graph to view" onClick={() => { view.current.auto = true; draw(); }}><Maximize2 aria-hidden className="size-4" /></Button>
        </div>
        {hover ? <Tooltip node={hover.node} x={hover.x} y={hover.y} width={sizeRef.current.w} /> : null}
        <Legend />
      </div>
      <aside className="space-y-3 text-[13px]">
        {selectedInfo ? (
          <div className="rounded-[10px] bg-surface-2 p-3">
            <div className="flex items-center justify-between">
              <p className="text-[15px] font-semibold">Cluster C{selectedInfo.cluster}</p>
              <Button variant="plain" onClick={() => setSelected(null)}>Clear</Button>
            </div>
            <p className="text-label-2">{selectedInfo.size.toLocaleString("en-IE")} frozen core samples · {selectedInfo.anomalies} anomalies nearest to it</p>
            <p className="mt-2 font-medium">Connected clusters</p>
            <ul className="mt-1 space-y-0.5">
              {(neighbours.get(selectedInfo.cluster) ?? []).sort((a, b) => a.distance - b.distance).slice(0, 8).map((n) => (
                <li key={n.cluster} className="flex justify-between">
                  <button type="button" className="text-accent" onClick={() => setSelected(n.cluster)}>C{n.cluster}</button>
                  <span className="tabular text-label-2">{n.distance.toFixed(2)}{n.kind === "nearest" ? " (nearest)" : ""}</span>
                </li>
              ))}
            </ul>
            {selectedAnomalies.length ? (
              <>
                <p className="mt-2 font-medium">Anomalies</p>
                <ul className="mt-1 max-h-56 space-y-1 overflow-auto">
                  {selectedAnomalies.map((a) => (
                    <li key={a.id}>
                      <Link className="text-accent" to={`/investigations/${encodeURIComponent(a.request_id ?? "")}`}>{a.sender} → {a.recipient}</Link>
                      <span className="tabular block text-[12px] text-label-2">{formatMoney(a.amount)} · risk {a.risk_score?.toFixed(1) ?? "—"} · {a.decision_label}</span>
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
          </div>
        ) : (
          <div className="rounded-[10px] bg-surface-2 p-3 text-label-2">
            Hover a node for details; rotation pauses while the pointer is over the graph. Click a cluster to highlight its connections,
            or click a diamond to open that request's investigation. Scroll to zoom, drag to pan.
          </div>
        )}
        <div className="grid grid-cols-2 gap-2">
          <Chip tone="accent">{data.summary.clusters} clusters</Chip>
          <Chip>{data.summary.core_samples.toLocaleString("en-IE")} cores</Chip>
          <Chip>{data.summary.near_links} cluster links</Chip>
          <Chip tone="verify">{data.summary.anomalies_shown} of {data.summary.anomalies_total} anomalies</Chip>
        </div>
        <p className="text-[12px] text-label-2">
          eps {data.summary.eps.toFixed(3)} · min_samples {data.summary.min_samples} · clusters linked when their nearest core samples are within{" "}
          {data.summary.link_distance.toFixed(2)} (2 × eps). {data.summary.note}
        </p>
      </aside>
    </div>
  );
}

function Legend() {
  const item = "flex items-center gap-1.5";
  return (
    <ul className="pointer-events-none absolute bottom-2 left-2 flex max-w-[calc(100%-1rem)] flex-wrap gap-x-3 gap-y-1 rounded-[8px] bg-black/70 px-2.5 py-1.5 text-[11px] text-[#d1d1d6] backdrop-blur">
      <li className={item}><span aria-hidden className="size-2.5 rounded-full" style={{ background: GRAPH.hub }} />Cluster (size = core samples)</li>
      <li className={item}><span aria-hidden className="size-1.5 rounded-full" style={{ background: GRAPH.core }} />Core sample</li>
      <li className={item}><span aria-hidden className="h-px w-4" style={{ background: GRAPH.edge }} />Link between nearby clusters</li>
      <li className={item}>
        <span aria-hidden className="flex gap-0.5">
          {Object.values(DECISION_COLOR).map((c) => <span key={c} className="size-2 rotate-45" style={{ background: c }} />)}
        </span>
        Anomaly: permitted · verify · preventive block · evidence
      </li>
      <li className={item}><span aria-hidden className="w-4 border-t border-dashed" style={{ borderColor: GRAPH.edge }} />Anomaly or nearest-cluster link</li>
    </ul>
  );
}

function Tooltip({ node, x, y, width }: { node: SimNode; x: number; y: number; width: number }) {
  const left = x > width - 260 ? x - 250 : x + 14;
  return (
    <div role="status" className="pointer-events-none absolute z-10 w-60 rounded-[10px] bg-surface p-3 text-[12px] shadow-xl ring-1 ring-separator" style={{ left, top: y + 12 }}>
      {node.kind === "anomaly" ? (
        <>
          <p className="font-semibold">{node.sender} → {node.recipient}</p>
          <p className="tabular text-label-2">{formatMoney(node.amount)} · risk {node.risk_score?.toFixed(1) ?? "—"}</p>
          <div className="my-1.5">{node.decision_label ? <DecisionBadge size="sm" label={node.decision_label} /> : null}</div>
          <p className="text-label-2">Outside every core neighbourhood: distance {node.distance?.toFixed(2)} to nearest cluster C{node.cluster}. Click to investigate.</p>
        </>
      ) : node.kind === "cluster" ? (
        <>
          <p className="font-semibold">Cluster C{node.cluster}</p>
          <p className="text-label-2">{node.size?.toLocaleString("en-IE")} frozen core samples from training profiles</p>
        </>
      ) : (
        <p className={cx("text-label-2")}>Core sample of cluster C{node.cluster} (training profile)</p>
      )}
    </div>
  );
}
