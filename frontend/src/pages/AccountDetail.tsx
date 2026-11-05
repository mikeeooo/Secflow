import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router";
import { useAccount } from "../api/hooks";
import { AssessmentRow } from "../components/AssessmentRow";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { Card, CardHeader, Chip, KeyValue, PageHeader } from "../components/ui";
import { formatDateTime, formatInt, formatMoney, humanize } from "../lib/format";

export function AccountDetailPage() {
  const { accountId = "" } = useParams();
  const { data, error, isPending, refetch } = useAccount(accountId);
  if (isPending) return <Card><LoadingState rows={8} /></Card>;
  if (error) return <Card><ErrorState error={error} onRetry={() => void refetch()} title="Couldn't load this account" /></Card>;
  const { account, profile, context, activity } = data;
  const latest = context.latest;
  return (
    <>
      <Link to="/accounts" className="mb-3 inline-flex items-center gap-1 text-[14px] font-medium text-accent"><ArrowLeft aria-hidden className="size-4" /> Accounts</Link>
      <PageHeader title={account.display_name} subtitle={`${account.account_id} · ${humanize(account.account_type)} account · ${account.home_country} · opened ${formatDateTime(account.created_at)}`} />
      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Behaviour profile" subtitle="Observed from assessed payment requests and sign-ins" />
          <div className="px-5 pb-4">
            <KeyValue items={[
              { label: "Requests sent", value: formatInt(profile.requests_sent) },
              { label: "Requests received", value: formatInt(profile.requests_received) },
              { label: "Median amount", value: formatMoney(profile.median_amount) },
              { label: "90th percentile amount", value: formatMoney(profile.p90_amount) },
              { label: "Typical hour (UTC)", value: profile.typical_hour == null ? "—" : `${profile.typical_hour.toFixed(1)} h` },
              { label: "Decisions", value: Object.entries(profile.decisions).map(([k, v]) => `${k} ${v}`).join(" · ") || "—" },
            ]} />
          </div>
        </Card>
        <Card>
          <CardHeader title="Account context (DBSCAN)" subtitle="Latest trailing 24-hour profile against frozen training cores" />
          <div className="space-y-3 px-5 pb-5 text-[14px]">
            {latest ? (
              <>
                <Chip tone={latest.status === "outside_context" ? "verify" : latest.status === "within_context" ? "permit" : "neutral"}>{humanize(latest.status)}</Chip>
                <p className="text-label-2">
                  {latest.status === "outside_context"
                    ? "The latest profile lies outside every frozen core neighbourhood. This adds context to the risk score; it is not a fraud verdict."
                    : latest.status === "within_context"
                      ? `The latest profile lies within a frozen core neighbourhood (cluster ${latest.cluster}).`
                      : "Too little history for a context comparison; the context score is 0."}
                </p>
                <p className="text-[12px] text-label-2">From <Link className="text-accent" to={`/investigations/${latest.request_id}`}>{latest.request_id}</Link> · {formatDateTime(latest.at)}</p>
                <p className="text-[13px] text-label-2">All requests: {Object.entries(context.counts).map(([k, v]) => `${humanize(k)} ${v}`).join(" · ")}</p>
              </>
            ) : <p className="text-label-2">No assessed requests from this account yet.</p>}
          </div>
        </Card>
      </div>
      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader title="Frequent recipients" />
          <ul className="px-5 pb-4">
            {profile.top_recipients.length ? profile.top_recipients.map((r) => (
              <li key={r.id} className="flex items-center justify-between border-b border-separator py-2 last:border-0">
                <span className="min-w-0 truncate">{r.kind === "account" ? <Link className="text-accent" to={`/accounts/${r.id}`}>{r.name}</Link> : r.name} <span className="text-[12px] text-label-2">{r.id}</span></span>
                <span className="tabular text-[14px] text-label-2">{r.payments} payments</span>
              </li>
            )) : <li className="py-2 text-label-2">No outgoing payments yet.</li>}
          </ul>
        </Card>
        <Card>
          <CardHeader title="Devices" subtitle="From sign-in events" />
          <ul className="px-5 pb-4">
            {profile.devices.length ? profile.devices.map((d) => (
              <li key={d.device_id} className="flex items-center justify-between gap-3 border-b border-separator py-2 last:border-0">
                <span className="font-mono text-[13px]">{d.device_id}</span>
                <span className="text-right text-[12px] text-label-2">first {formatDateTime(d.first_seen)}<br />{d.sign_ins} sign-ins</span>
              </li>
            )) : <li className="py-2 text-label-2">No sign-ins recorded.</li>}
          </ul>
        </Card>
      </div>
      <Card className="mt-5">
        <CardHeader title="Linked transfers" subtitle="Most recent requests sent or received by this account" />
        {activity.length ? <ul>{activity.map((item) => <AssessmentRow key={item.request_id} item={item} />)}</ul> : <EmptyState title="No linked transfers" />}
      </Card>
    </>
  );
}
