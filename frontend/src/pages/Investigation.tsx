import { ArrowLeft, CheckCircle2, XCircle } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router";
import { ApiError } from "../api/client";
import { useInvestigation, useReview } from "../api/hooks";
import type { AssessmentDetail, Investigation, TimelineEntry } from "../api/types";
import { DecisionBadge, LABEL_STYLE } from "../components/DecisionBadge";
import { RiskComposition } from "../components/RiskComposition";
import { ErrorState, LoadingState, errorMessage } from "../components/States";
import { Button, Card, CardHeader, Chip, Field, KeyValue, PageHeader, Segmented, cx, inputClass } from "../components/ui";
import { FAMILY_TEXT, LABEL_HINT, OUTCOME_TEXT, SOURCE_TEXT, formatDateTime, formatMoney, humanize } from "../lib/format";

export function InvestigationPage() {
  const { requestId = "" } = useParams();
  const { data, error, isPending, refetch } = useInvestigation(requestId);
  if (isPending) return <Card><LoadingState rows={10} label="Loading investigation" /></Card>;
  if (error) {
    const missing = error instanceof ApiError && error.status === 404;
    return (
      <Card>
        <ErrorState error={error} title={missing ? `No request with ID ${requestId}` : "Couldn't load this investigation"} onRetry={missing ? undefined : () => void refetch()} />
      </Card>
    );
  }
  const a = data.assessment;
  return (
    <>
      <Link to="/transactions" className="mb-3 inline-flex items-center gap-1 text-[14px] font-medium text-accent">
        <ArrowLeft aria-hidden className="size-4" /> Transactions
      </Link>
      <PageHeader
        title={`${a.sender.name} → ${a.recipient.name}`}
        subtitle={`${formatMoney(a.amount)} · ${formatDateTime(a.event_time)} · ${a.request_id} · ${a.origin === "simulation" ? "simulated request" : "demonstration history"}`}
      />
      <DecisionPanel a={a} />
      <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="min-w-0 space-y-5">
          <Card className="p-5">
            <RiskComposition details={a.component_details} total={a.risk_score} verify={a.thresholds.verify} block={a.thresholds.block} />
          </Card>
          <ComponentsTable a={a} />
          <Reasons a={a} />
          <Facts a={a} />
        </div>
        <div className="min-w-0 space-y-5">
          <ReviewPanel data={data} />
          <Card>
            <CardHeader title="Payment details" />
            <div className="px-5 pb-4">
              <KeyValue items={[
                { label: "Sender", value: a.sender.kind === "account" ? <Link className="text-accent" to={`/accounts/${a.sender.id}`}>{a.sender.name}</Link> : a.sender.name },
                { label: "Recipient", value: a.recipient.kind === "account" ? <Link className="text-accent" to={`/accounts/${a.recipient.id}`}>{a.recipient.name}</Link> : `${a.recipient.name} (${a.recipient.id})` },
                { label: "Amount", value: formatMoney(a.amount) },
                { label: "Sign-in", value: humanize(a.auth_method) },
                { label: "Device", value: <span className="font-mono text-[12px]">{a.device_id}</span> },
                { label: "Session", value: <span className="font-mono text-[12px]">{a.session_id}</span> },
                { label: "Session country", value: a.ip_country },
                { label: "Channel", value: humanize(a.channel) },
              ]} />
            </div>
          </Card>
          <Timeline entries={data.timeline} />
        </div>
      </div>
    </>
  );
}

function DecisionPanel({ a }: { a: AssessmentDetail }) {
  const style = LABEL_STYLE[a.decision_label];
  return (
    <Card className={cx("overflow-hidden")}>
      <div className={cx("flex flex-wrap items-start gap-4 p-5", a.decision_label === "Confirmed fraud evidence" ? "bg-evidence-soft" : style.soft)}>
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <DecisionBadge label={a.decision_label} />
            <Chip>Decided by: {SOURCE_TEXT[a.decision_source]}</Chip>
            <Chip>{OUTCOME_TEXT[a.outcome]}</Chip>
          </div>
          <p className="text-[16px] font-medium">{a.explanation}</p>
          <p className="text-[13px] text-label-2">{LABEL_HINT[a.decision_label]}</p>
          {a.status_notes.map((note) => (
            <p key={note} className="text-[13px] text-label-2">{note}</p>
          ))}
          {a.corroborating_signals.length ? (
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              <span className="text-[13px] text-label-2">Corroborating behaviour:</span>
              {a.corroborating_signals.map((family) => <Chip key={family} tone="accent">{FAMILY_TEXT[family] ?? humanize(family)}</Chip>)}
              <span className="text-[12px] text-label-2">(a preventive block needs {a.thresholds.min_corroborating_families} distinct families)</span>
            </div>
          ) : null}
        </div>
      </div>
      {a.evidence.length ? (
        <div className="border-t border-separator p-5">
          <h2 className="mb-2 text-[15px] font-semibold">Active security evidence at request time</h2>
          <ul className="space-y-2">
            {a.evidence.map((e) => (
              <li key={e.evidence_id} className="rounded-[10px] bg-surface-2 p-3 text-[14px]">
                <p className="font-medium">{humanize(e.evidence_type)} · {e.entity_type} {e.entity_id}</p>
                <p className="text-[13px] text-label-2">
                  {e.evidence_id} · source {humanize(e.source)} · recorded {formatDateTime(e.recorded_at)} · effective from {formatDateTime(e.effective_from)}
                  {e.effective_until ? ` until ${formatDateTime(e.effective_until)}` : ""}
                </p>
                <p className="text-[13px] text-label-2">{e.note}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="border-t border-separator px-5 py-3 text-[13px] text-label-2">
          No active trusted security evidence applied. The anomaly score describes how unusual this request is; a high score alone is not confirmed fraud.
        </p>
      )}
    </Card>
  );
}

function ComponentsTable({ a }: { a: AssessmentDetail }) {
  return (
    <Card>
      <CardHeader title="Model components" subtitle="Each model runs once per assessment; the policy only combines the results" />
      <div className="overflow-x-auto px-5 pb-4">
        <table className="tabular w-full min-w-[560px] text-left text-[14px]">
          <thead className="text-[12px] text-label-2">
            <tr>
              <th className="py-2 pr-3 font-medium">Component</th>
              <th className="py-2 pr-3 text-right font-medium">Score</th>
              <th className="py-2 pr-3 text-right font-medium">Weight</th>
              <th className="py-2 pr-3 text-right font-medium">Points</th>
              <th className="py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {a.component_details.map((c) => (
              <tr key={c.key} className="border-t border-separator align-top">
                <td className="py-2.5 pr-3">
                  <p className="font-medium">{c.label}</p>
                  <p className="max-w-md text-[12px] text-label-2">{c.detail}</p>
                </td>
                <td className="py-2.5 pr-3 text-right">{c.score == null ? "—" : c.score.toFixed(3)}</td>
                <td className="py-2.5 pr-3 text-right">{c.weight.toFixed(2)}</td>
                <td className="py-2.5 pr-3 text-right font-semibold">{c.contribution == null ? "—" : c.contribution.toFixed(2)}</td>
                <td className="py-2.5 text-[13px] text-label-2">{c.status ? humanize(c.status) : "—"}{c.raw != null ? <><br />raw {c.raw.toFixed(3)}</> : null}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function Reasons({ a }: { a: AssessmentDetail }) {
  return (
    <Card>
      <CardHeader title="Behaviour rules" subtitle={`Rules score ${a.components.rules?.toFixed(2) ?? "—"} (capped sum of triggered weights)`} />
      {a.reasons.length ? (
        <ul className="px-5 pb-4">
          {a.reasons.map((r) => (
            <li key={r.code} className="border-t border-separator py-3 first:border-0">
              <div className="flex flex-wrap items-center gap-2">
                <code className="text-[12px] font-semibold">{r.code}</code>
                <Chip tone={r.corroborating ? "accent" : "neutral"}>{FAMILY_TEXT[r.family] ?? humanize(r.family)}</Chip>
                <span className="tabular text-[12px] text-label-2">+{r.weight.toFixed(2)}</span>
                {r.corroborating ? <span className="text-[12px] text-label-2">counts toward corroboration</span> : null}
              </div>
              <p className="mt-1 text-[14px]">{r.description}</p>
              <p className="text-[13px] text-label-2">{r.detail}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="px-5 pb-5 text-[14px] text-label-2">No behaviour rule triggered.</p>
      )}
    </Card>
  );
}

const FACT_LABELS: Record<string, string> = {
  prior_requests_total: "Earlier requests",
  prior_requests_30d: "Requests in the last 30 days",
  median_amount_30d: "30-day median amount",
  amount_zscore_30d: "Amount z-score (30 days)",
  requests_1h: "Requests in the last hour",
  requests_24h: "Requests in the last 24 hours",
  velocity_ratio_24h: "Pace versus usual",
  new_recipient: "No established beneficiary history",
  recipient_senders_24h: "Other senders to beneficiary (24 h)",
  device_change: "Device change",
  auth_failures_24h: "Failed sign-ins (24 h)",
  incoming_24h: "Funds received (24 h)",
  hours_since_last_request: "Hours since previous request",
};

function Facts({ a }: { a: AssessmentDetail }) {
  const show = (value: unknown) => (value == null ? "—" : typeof value === "boolean" ? (value ? "Yes" : "No") : String(value));
  return (
    <Card>
      <details>
        <summary className="cursor-pointer px-5 py-4 text-[17px] font-semibold">Observed facts at request time</summary>
        <div className="px-5 pb-4">
          <p className="mb-2 text-[13px] text-label-2">Computed only from events before this request. Labels and generator metadata are never inputs.</p>
          <KeyValue items={Object.entries(a.facts).map(([k, v]) => ({ label: FACT_LABELS[k] ?? humanize(k), value: show(v) }))} />
        </div>
      </details>
    </Card>
  );
}

function Timeline({ entries }: { entries: TimelineEntry[] }) {
  return (
    <Card>
      <CardHeader title="Timeline" subtitle="Simulation time, UTC" />
      <ol className="px-5 pb-4">
        {entries.map((e, i) => (
          <li key={`${e.kind}-${i}`} className="relative border-l border-separator pb-4 pl-4 last:pb-0">
            <span aria-hidden className={cx("absolute top-1.5 -left-[5px] size-2.5 rounded-full",
              e.kind === "decision" ? "bg-accent" : e.kind === "evidence" ? "bg-evidence" : e.kind === "review" ? "bg-permit" : "bg-label-2")} />
            <p className="text-[14px] font-medium">{e.title}</p>
            <p className="text-[12px] text-label-2">{formatDateTime(e.at)}</p>
            {e.detail ? <p className="text-[13px] text-label-2">{e.detail}</p> : null}
          </li>
        ))}
      </ol>
    </Card>
  );
}

function ReviewPanel({ data }: { data: Investigation }) {
  const a = data.assessment;
  const review = useReview(a.request_id);
  const [action, setAction] = useState<"approve" | "reject">("approve");
  const [reason, setReason] = useState("");
  const [actor, setActor] = useState("Local analyst");
  const [touched, setTouched] = useState(false);
  const reasonError = touched && reason.trim().length < 8 ? "Give a reason of at least 8 characters." : undefined;

  if (a.decision !== "Verify") {
    return (
      <Card>
        <CardHeader title="Review" />
        <p className="px-5 pb-5 text-[14px] text-label-2">Only requests whose automated decision is Needs verification are reviewed. This assessment is recorded as it was decided.</p>
      </Card>
    );
  }

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setTouched(true);
    if (reason.trim().length < 8 || review.isPending) return;
    review.mutate({ action, reason: reason.trim(), actor: actor.trim() || "Local analyst" });
  };

  return (
    <Card>
      <CardHeader title="Review" subtitle="The original automated decision and score stay unchanged" />
      {data.reviews.length ? (
        <ul className="px-5 pb-4">
          {data.reviews.map((r) => (
            <li key={r.review_id} className="rounded-[10px] bg-surface-2 p-3">
              <p className="flex items-center gap-1.5 font-semibold">
                {r.action === "approve" ? <CheckCircle2 aria-hidden className="size-4 text-permit" /> : <XCircle aria-hidden className="size-4 text-block" />}
                {OUTCOME_TEXT[r.resulting_outcome]}
              </p>
              <p className="mt-1 text-[14px]">“{r.reason}”</p>
              <p className="mt-1 text-[12px] text-label-2">
                {r.actor} · {formatDateTime(r.created_at)} · {r.review_id}<br />
                Original decision {r.original_decision} at risk {r.original_risk_score?.toFixed(1) ?? "—"}
              </p>
            </li>
          ))}
        </ul>
      ) : null}
      {data.can_review ? (
        <form onSubmit={submit} className="space-y-4 px-5 pb-5" noValidate>
          <Segmented label="Review outcome" stretch value={action} onChange={setAction}
            options={[{ value: "approve", label: "Approve" }, { value: "reject", label: "Reject" }]} />
          <Field label="Reason (required)" htmlFor="review-reason" error={reasonError} hint="Recorded in the audit trail.">
            <textarea id="review-reason" rows={3} className={cx(inputClass, "py-2")} value={reason} aria-invalid={!!reasonError || undefined}
              onChange={(e) => setReason(e.target.value)} onBlur={() => setTouched(true)} placeholder="For example: customer confirmed the payee by phone" />
          </Field>
          <Field label="Reviewer" htmlFor="review-actor" hint="A display name for this local workflow; not an authenticated identity.">
            <input id="review-actor" className={inputClass} value={actor} onChange={(e) => setActor(e.target.value)} />
          </Field>
          {review.error ? <p role="alert" className="text-[13px] text-block">{errorMessage(review.error)}</p> : null}
          <Button type="submit" variant={action === "approve" ? "primary" : "destructive"} disabled={review.isPending} className="w-full">
            {review.isPending ? "Saving…" : action === "approve" ? "Approve payment" : "Reject payment"}
          </Button>
        </form>
      ) : null}
    </Card>
  );
}
