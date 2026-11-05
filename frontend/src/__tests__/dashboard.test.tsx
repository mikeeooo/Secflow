import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ClusterGraph as GraphData, Dashboard } from "../api/types";
import { ClusterGraph } from "../components/ClusterGraph";
import { Gauge, TimeSeries } from "../components/dashboard";
import { MonitoringDashboard } from "../components/MonitoringDashboard";
import { mockFetch, renderAt } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

const bucket = (t: string, overrides: Partial<Dashboard["series"][number]> = {}) => ({
  t, requests: 100, permit: 90, verify: 8, block_risk: 1, block_evidence: 1, safeguard: 0, outside_context: 6, scored: 100,
  completed_amount: 4_000, pending_amount: 300, blocked_amount: 50, mean_isolation_forest: 0.5, mean_lof: 0.5,
  mean_rules: 0.05, latency_mean_ms: 4.2, latency_max_ms: 6, risk_p50: 30, risk_p90: 55, risk_p99: 80, ...overrides,
});

const dashboard = (window: "history" | "live"): Dashboard => ({
  window, label: window === "live" ? "Simulations, last 30 simulated minutes, per minute" : "Daily",
  bucket_seconds: window === "live" ? 60 : 86_400,
  range: { from: "2026-07-20T00:00:00Z", to: "2026-07-22T00:00:00Z" },
  series: [bucket("2026-07-20T00:00:00Z"), bucket("2026-07-21T00:00:00Z", { verify: 12 })],
  totals: { requests: 200, verify_rate: 0.1, block_rate: 0.02, outside_context_rate: 0.06, preventive_blocks: 2, evidence_blocks: 2, latency_mean_ms: 4.2, latency_p95_ms: 5.9 },
  decision_sources: { risk_policy: 196, confirmed_fraud_evidence: 2, assessment_safeguard: 2 },
  rule_triggers: [{ code: "NEW_BENEFICIARY", count: 40, share: 0.2 }, { code: "VELOCITY_BURST", count: 5, share: 0.025 }],
  thresholds: { verify: 61, block: 97 },
  goals: { max_verify_rate: 0.05 },
});

describe("dashboard panels", () => {
  it("labels a gauge with its formatted value", () => {
    render(<Gauge label="Verify rate" value={0.104} max={0.2} format={(v) => `${(v * 100).toFixed(1)}%`} bands={[{ to: 0.05, color: "green" }, { to: 0.2, color: "red" }]} />);
    expect(screen.getByRole("img", { name: "Verify rate: 10.4%" })).toBeInTheDocument();
  });

  it("shows mean, max and last for each series and skips gaps", () => {
    render(
      <TimeSeries
        title="Scores"
        xFormat={(t) => t}
        series={[{ key: "a", label: "Isolation Forest", color: "blue" }]}
        points={[{ t: "1", values: { a: 0.2 } }, { t: "2", values: { a: null } }, { t: "3", values: { a: 0.6 } }]}
      />,
    );
    const row = screen.getByText("Isolation Forest").closest("tr")!;
    expect(row).toHaveTextContent("0.40");
    expect(row).toHaveTextContent("0.60");
  });

  it("switches between the full history and the live window", async () => {
    const calls = mockFetch((url) => ({ body: dashboard(url.includes("live") ? "live" : "history") }));
    renderAt(<MonitoringDashboard />);
    expect(await screen.findByRole("img", { name: "Verify rate: 10.0%" })).toBeInTheDocument();
    expect(screen.getByText("New payee")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: /Last 30 min/ }));
    await waitFor(() => expect(calls.some((c) => c.url === "/api/dashboard?window=live")).toBe(true));
    expect(await screen.findByText(/Auto-refresh 5 s/)).toBeInTheDocument();
  });
});

const graph: GraphData = {
  nodes: [
    { id: "c1", kind: "cluster", cluster: 1, size: 500 },
    { id: "c2", kind: "cluster", cluster: 2, size: 80 },
    { id: "m1-0", kind: "core", cluster: 1 },
    { id: "a:REQ-9", kind: "anomaly", cluster: 1, request_id: "REQ-9", decision_label: "Needs verification", risk_score: 74.2,
      distance: 2.4, sender: "Amara Okafor", recipient: "Harbor Lane Utilities", amount: 950, event_time: "2026-10-28T00:00:00Z", origin: "simulation" },
  ],
  edges: [
    { source: "c1", target: "c2", kind: "near", distance: 1.2, pairs: 4 },
    { source: "c1", target: "m1-0", kind: "member", distance: 0.3, pairs: 0 },
    { source: "c1", target: "a:REQ-9", kind: "anomaly", distance: 2.4, pairs: 0 },
  ],
  clusters: [{ cluster: 1, size: 500, anomalies: 1 }, { cluster: 2, size: 80, anomalies: 0 }],
  summary: { clusters: 2, core_samples: 580, eps: 0.89, min_samples: 5, link_distance: 1.78, near_links: 1, nearest_links: 0,
    training_noise_fraction: 0.067, anomalies_total: 1, anomalies_shown: 1, note: "Context, not a fraud verdict." },
};

describe("ClusterGraph", () => {
  it("describes the network for assistive technology without needing a canvas", () => {
    renderAt(<ClusterGraph data={graph} showCores />);
    expect(screen.getByRole("img", { name: /2 DBSCAN clusters with 1 links between nearby clusters and 1 anomalous profiles/ })).toBeInTheDocument();
    expect(screen.getByText("2 clusters")).toBeInTheDocument();
    expect(screen.getByText("1 of 1 anomalies")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Fit graph to view" })).toBeEnabled();
  });
});
