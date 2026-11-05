import { ArrowRight } from "lucide-react";
import { Link } from "react-router";
import { useOverview } from "../api/hooks";
import { AssessmentRow } from "../components/AssessmentRow";
import { ColumnChart, LineChart, ShareBar } from "../components/charts";
import { StreamControls } from "../components/StreamControls";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { Card, CardHeader, PageHeader, Stat } from "../components/ui";
import { formatCompactMoney, formatDateTime, formatDay, formatInt, formatMoney } from "../lib/format";

export function OverviewPage() {
  const { data, error, isPending, refetch } = useOverview();
  return (
    <>
      <PageHeader
        title="Overview"
        subtitle={data ? `Simulation time ${formatDateTime(data.simulation_time)}` : "Assessments, decisions, and the review queue"}
        action={<StreamControls compact />}
      />
      {isPending ? (
        <Card><LoadingState rows={6} /></Card>
      ) : error ? (
        <Card><ErrorState error={error} onRetry={() => void refetch()} /></Card>
      ) : (
        <div className="space-y-5">
          <Card className="grid grid-cols-2 gap-6 p-5 md:grid-cols-5">
            <Stat label="Assessed requests" value={formatInt(data.totals.assessed)} hint={`${formatInt(data.totals.simulations)} simulated this session`} />
            <Stat label="Permitted" value={formatInt(data.totals.permitted)} tone="permit" />
            <Stat label="Needs verification" value={formatInt(data.totals.needs_verification)} tone="verify" hint={`${formatInt(data.totals.awaiting_review)} awaiting review`} />
            <Stat label="Preventive risk blocks" value={formatInt(data.totals.preventive_blocks)} tone="block" />
            <Stat label="Confirmed-evidence blocks" value={formatInt(data.totals.confirmed_evidence_blocks)} tone="evidence" />
          </Card>

          <div className="grid gap-5 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader title="Daily verifications and blocks" subtitle="Requests per day that were not simply permitted" />
              <div className="px-5 pb-5">
                <ColumnChart
                  title="Verifications and blocks per day"
                  columns={data.trend.map((d) => ({ label: formatDay(d.date), values: { verify: d.verify, block: d.block } }))}
                  series={[
                    { key: "verify", label: "Needs verification", swatch: "bg-verify" },
                    { key: "block", label: "Blocked", swatch: "bg-block" },
                  ]}
                  xLabels={data.trend.length ? [formatDay(data.trend[0].date), formatDay(data.trend[data.trend.length - 1].date)] : undefined}
                />
              </div>
            </Card>
            <Card>
              <CardHeader title="Payment volume" subtitle="Simulated outcomes only; no funds move" />
              <div className="space-y-4 px-5 pb-5">
                <Stat label="Completed (permitted or approved)" value={formatCompactMoney(data.volumes.completed)} hint={formatMoney(data.volumes.completed)} />
                <Stat label="Held for verification" value={formatCompactMoney(data.volumes.pending_verification)} tone="verify" />
                <Stat label="Blocked or rejected attempts" value={formatCompactMoney(data.volumes.blocked_attempts)} tone="block" hint="Excluded from completed totals" />
              </div>
            </Card>
          </div>

          <div className="grid gap-5 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader title="Mean anomaly risk per day" subtitle="Average 0–100 index across assessed requests" />
              <div className="px-5 pb-5">
                <LineChart
                  title="Mean anomaly risk per day"
                  points={data.trend.map((d) => ({ label: formatDay(d.date), value: d.mean_risk }))}
                  yMax={100}
                  xLabels={data.trend.length ? [formatDay(data.trend[0].date), formatDay(data.trend[data.trend.length - 1].date)] : undefined}
                />
              </div>
            </Card>
            <Card>
              <CardHeader title="Decision mix" />
              <div className="px-5 pb-5">
                <ShareBar
                  parts={[
                    { key: "p", label: "Permitted", value: data.totals.permitted, swatch: "bg-permit" },
                    { key: "v", label: "Needs verification", value: data.totals.needs_verification, swatch: "bg-verify" },
                    { key: "b", label: "Preventive block", value: data.totals.preventive_blocks, swatch: "bg-block" },
                    { key: "e", label: "Confirmed evidence", value: data.totals.confirmed_evidence_blocks, swatch: "bg-evidence" },
                  ]}
                />
              </div>
            </Card>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <CardHeader
                title="Review queue"
                subtitle="Highest-risk requests awaiting an analyst"
                action={<Link className="inline-flex items-center gap-1 text-[14px] font-medium text-accent" to="/transactions?review_status=pending&sort=risk_desc">All pending <ArrowRight aria-hidden className="size-4" /></Link>}
              />
              {data.review_queue.length ? (
                <ul>{data.review_queue.map((item) => <AssessmentRow key={item.request_id} item={item} compact />)}</ul>
              ) : (
                <EmptyState title="Nothing to review">Requests that need verification will appear here.</EmptyState>
              )}
            </Card>
            <Card>
              <CardHeader
                title="Recent activity"
                action={<Link className="inline-flex items-center gap-1 text-[14px] font-medium text-accent" to="/live">Live transfers <ArrowRight aria-hidden className="size-4" /></Link>}
              />
              <ul>{data.recent.map((item) => <AssessmentRow key={item.request_id} item={item} compact />)}</ul>
            </Card>
          </div>
        </div>
      )}
    </>
  );
}
