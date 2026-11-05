import { Clock, RefreshCw } from "lucide-react";
import { useState } from "react";
import { useDashboard } from "../api/hooks";
import type { DashboardBucket, DashboardWindow } from "../api/types";
import { ColumnChart } from "./charts";
import { BarGauge, Gauge, Panel, Stat, TimeSeries } from "./dashboard";
import { ErrorState, LoadingState } from "./States";
import { Segmented } from "./ui";
import { formatCompactMoney, formatInt, formatPercent } from "../lib/format";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

const RULE_SHORT: Record<string, string> = {
  NEW_BENEFICIARY: "New payee",
  NEW_BENEFICIARY_HIGH_AMOUNT: "New payee, high amount",
  NEW_DEVICE: "New device",
  FOREIGN_SESSION: "Foreign session",
  VELOCITY_BURST: "Velocity burst",
  AMOUNT_ELEVATED: "Amount elevated",
  AMOUNT_SPIKE: "Amount spike",
  SHARED_NEW_BENEFICIARY: "Shared new payee",
  REPEATED_FAILED_LOGINS: "Failed sign-ins",
  NEW_DEVICE_AFTER_FAILED_LOGINS: "New device + failures",
  PASS_THROUGH_FUNDS: "Pass-through funds",
  RECIPIENT_FANOUT: "Recipient fan-out",
};

function axisFormatter(window: DashboardWindow) {
  return (iso: string) => {
    const date = new Date(iso);
    return window === "live"
      ? date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "UTC" })
      : date.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
  };
}

function pick(series: DashboardBucket[], keys: (keyof DashboardBucket)[]) {
  return series.map((b) => ({ t: b.t, values: Object.fromEntries(keys.map((k) => [k, b[k] as number | null])) }));
}

/** Grafana-style monitoring view over the recorded assessments. */
export function MonitoringDashboard() {
  const [window, setWindow] = useState<DashboardWindow>("history");
  const { data, error, isPending, isFetching, refetch } = useDashboard(window);
  const x = axisFormatter(window);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="flex items-center gap-1.5 text-[13px] text-label-2">
          <Clock aria-hidden className="size-4" />
          {data ? `${x(data.range.from)} – ${x(data.range.to)} · ${data.label}` : "Loading range…"}
          {window === "live" ? (
            <span className="ml-2 inline-flex items-center gap-1 text-accent">
              <RefreshCw aria-hidden className={isFetching ? "size-3.5 animate-spin" : "size-3.5"} /> Auto-refresh 5 s
            </span>
          ) : null}
        </p>
        <Segmented
          label="Time range"
          value={window}
          onChange={setWindow}
          options={[
            { value: "history", label: "Full history · daily" },
            { value: "live", label: "Last 30 min · live" },
          ]}
        />
      </div>

      {isPending ? (
        <LoadingState rows={8} />
      ) : error ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-6 xl:grid-cols-12">
          <Panel title="Requests" className="md:col-span-2" info={window === "live" ? "simulations" : undefined}>
            <Stat value={formatInt(data.totals.requests)} color="var(--sf-accent)" spark={data.series.map((b) => b.requests)} caption="per bucket" />
          </Panel>
          <Panel title="Verify rate" className="md:col-span-2">
            <Gauge
              label="Verify rate"
              value={data.totals.verify_rate}
              max={0.2}
              format={pct}
              bands={[
                { to: data.goals.max_verify_rate ?? 0.05, color: "var(--sf-permit)" },
                { to: 0.1, color: "var(--sf-verify)" },
                { to: 0.2, color: "var(--sf-block)" },
              ]}
              caption={`goal ≤ ${formatPercent(data.goals.max_verify_rate, 0)}`}
            />
          </Panel>
          <Panel title="Outside context" className="md:col-span-2">
            <Gauge
              label="Share of profiles outside every frozen core neighbourhood"
              value={data.totals.outside_context_rate}
              max={0.2}
              format={pct}
              bands={[
                { to: 0.07, color: "var(--sf-permit)" },
                { to: 0.12, color: "var(--sf-verify)" },
                { to: 0.2, color: "var(--sf-block)" },
              ]}
              caption="training noise ≈ 6.7%"
            />
          </Panel>
          <Panel title="Preventive blocks" className="md:col-span-2">
            <Stat value={formatInt(data.totals.preventive_blocks)} color="var(--sf-block)" spark={data.series.map((b) => b.block_risk)} caption="risk policy, corroborated" />
          </Panel>
          <Panel title="Evidence blocks" className="md:col-span-2">
            <Stat value={formatInt(data.totals.evidence_blocks)} color="var(--sf-label)" spark={data.series.map((b) => b.block_evidence)} caption="trusted security evidence" />
          </Panel>
          <Panel title="Latency" className="md:col-span-2">
            <Stat
              value={data.totals.latency_mean_ms == null ? "—" : `${data.totals.latency_mean_ms.toFixed(1)} ms`}
              color="var(--sf-rules)"
              spark={data.series.map((b) => b.latency_mean_ms)}
              caption={data.totals.latency_p95_ms == null ? "no simulations yet" : `simulations · p95 ${data.totals.latency_p95_ms.toFixed(1)} ms`}
            />
          </Panel>

          <Panel title="Model scores · mean per bucket" className="col-span-2 md:col-span-6 xl:col-span-7">
            <TimeSeries
              title="Mean component scores"
              points={pick(data.series, ["mean_isolation_forest", "mean_lof", "mean_rules"])}
              series={[
                { key: "mean_isolation_forest", label: "Isolation Forest", color: "var(--sf-if)", fill: true },
                { key: "mean_lof", label: "Local Outlier Factor", color: "var(--sf-lof)" },
                { key: "mean_rules", label: "Behaviour rules", color: "var(--sf-rules)" },
              ]}
              yMax={1}
              xFormat={x}
            />
          </Panel>
          <Panel title="Rule triggers" className="col-span-2 md:col-span-6 xl:col-span-5" info="top 8 in window">
            <BarGauge
              color="var(--sf-accent)"
              format={(v) => formatInt(v)}
              items={data.rule_triggers.map((r) => ({ label: RULE_SHORT[r.code] ?? r.code, value: r.count, hint: `${r.code}: ${formatPercent(r.share)} of requests` }))}
            />
          </Panel>

          <Panel title="Anomaly-risk index percentiles" className="col-span-2 md:col-span-6 xl:col-span-7">
            <TimeSeries
              title="Risk index percentiles per bucket"
              points={pick(data.series, ["risk_p50", "risk_p90", "risk_p99"])}
              series={[
                { key: "risk_p50", label: "p50", color: "var(--sf-accent)", opacity: 0.4, fill: true },
                { key: "risk_p90", label: "p90", color: "var(--sf-accent)", opacity: 0.7 },
                { key: "risk_p99", label: "p99", color: "var(--sf-accent)" },
              ]}
              yMax={100}
              yFormat={(v) => v.toFixed(0)}
              xFormat={x}
              references={[
                { value: data.thresholds.verify, label: `Verify ${data.thresholds.verify}`, color: "var(--sf-verify)" },
                { value: data.thresholds.block, label: `Block ${data.thresholds.block}`, color: "var(--sf-block)" },
              ]}
            />
          </Panel>
          <Panel title="Requests needing attention" className="col-span-2 md:col-span-6 xl:col-span-5">
            <ColumnChart
              title="Verify and block decisions per bucket"
              height={230}
              columns={data.series.map((b) => ({ label: x(b.t), values: { verify: b.verify, block_risk: b.block_risk, block_evidence: b.block_evidence } }))}
              series={[
                { key: "verify", label: "Needs verification", swatch: "bg-verify" },
                { key: "block_risk", label: "Preventive block", swatch: "bg-block" },
                { key: "block_evidence", label: "Confirmed evidence", swatch: "bg-evidence" },
              ]}
              xLabels={data.series.length ? [x(data.series[0].t), x(data.series[data.series.length - 1].t)] : undefined}
            />
          </Panel>

          <Panel title="Simulated payment volume by outcome" className="col-span-2 md:col-span-6 xl:col-span-8" info="no funds move">
            <ColumnChart
              title="Volume per bucket by outcome"
              height={200}
              valueFormat={(v) => formatCompactMoney(v)}
              columns={data.series.map((b) => ({ label: x(b.t), values: { completed: b.completed_amount, pending: b.pending_amount, blocked: b.blocked_amount } }))}
              series={[
                { key: "completed", label: "Completed", swatch: "bg-permit" },
                { key: "pending", label: "Held for verification", swatch: "bg-verify" },
                { key: "blocked", label: "Blocked or rejected", swatch: "bg-block" },
              ]}
              xLabels={data.series.length ? [x(data.series[0].t), x(data.series[data.series.length - 1].t)] : undefined}
            />
          </Panel>
          <Panel title="Assessment latency per bucket" className="col-span-2 md:col-span-6 xl:col-span-4" info="ms">
            <TimeSeries
              title="Assessment latency"
              height={170}
              points={pick(data.series, ["latency_mean_ms", "latency_max_ms"])}
              series={[
                { key: "latency_mean_ms", label: "mean", color: "var(--sf-rules)", fill: true },
                { key: "latency_max_ms", label: "max", color: "var(--sf-dbscan)" },
              ]}
              yFormat={(v) => v.toFixed(1)}
              xFormat={x}
            />
          </Panel>
        </div>
      )}
    </div>
  );
}
