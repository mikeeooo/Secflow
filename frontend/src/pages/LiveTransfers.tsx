import { ArrowRight, WifiOff } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router";
import { useHealth } from "../api/hooks";
import type { AssessmentSummary, ComponentView } from "../api/types";
import { DecisionBadge } from "../components/DecisionBadge";
import { COMPONENTS, ComponentMiniBar, RiskComposition } from "../components/RiskComposition";
import { StreamControls } from "../components/StreamControls";
import { EmptyState, LoadingState, errorMessage } from "../components/States";
import { Card, CardHeader, Chip, KeyValue, PageHeader, cx } from "../components/ui";
import { FAMILY_TEXT, OUTCOME_TEXT, SOURCE_TEXT, formatDateTime, formatMoney, formatTime } from "../lib/format";
import { useLiveFeed } from "../lib/useLiveFeed";

function detailsFrom(item: AssessmentSummary): ComponentView[] {
  return COMPONENTS.map((c) => {
    const score = item.components[c.key];
    return { key: c.key, label: c.label, score, weight: c.weight, contribution: score == null ? null : 100 * c.weight * score, raw: null, status: null, detail: "" };
  });
}

export function LiveTransfersPage() {
  const feed = useLiveFeed();
  const point = useHealth().data?.policy?.operating_point;
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = feed.items.find((i) => i.request_id === selectedId) ?? feed.items[0] ?? null;
  const sources = useMemo(() => {
    const counts = { risk_policy: 0, confirmed_fraud_evidence: 0, assessment_safeguard: 0 };
    for (const item of feed.items) counts[item.decision_source] += 1;
    return counts;
  }, [feed.items]);

  return (
    <>
      <PageHeader
        title="Live Transfers"
        subtitle={`Simulated payment requests assessed as they arrive. Updates every 2 seconds${feed.simulationTime ? ` · simulation time ${formatDateTime(feed.simulationTime)}` : ""}.`}
        action={<StreamControls status={feed.stream ?? undefined} />}
      />
      {feed.error ? (
        <div role="alert" className="mb-4 flex items-center gap-2 rounded-[12px] bg-verify-soft px-4 py-3 text-[14px]">
          <WifiOff aria-hidden className="size-4 text-verify" />
          <span>Live updates are unavailable ({errorMessage(feed.error)}). Retrying automatically; Stop and Start still work.</span>
        </div>
      ) : null}
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader title="Incoming assessments" subtitle={`${feed.items.length} shown, newest first`} />
          {!feed.loaded ? <LoadingState rows={6} /> : feed.items.length === 0 ? (
            <EmptyState title="No simulated transfers yet" action={<Link className="text-[14px] font-medium text-accent" to="/simulator">Open the simulator</Link>}>
              The backend stream starts with the server. If it is stopped, press Start, or submit a payment from the simulator.
            </EmptyState>
          ) : (
            <ul aria-live="off">
              {feed.items.map((item) => (
                <li key={item.request_id} className={cx("border-b border-separator last:border-0", feed.fresh.has(item.request_id) && "sf-arrive")}>
                  <button type="button" onClick={() => setSelectedId(item.request_id)} aria-pressed={selected?.request_id === item.request_id}
                    className={cx("grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 px-5 py-3 text-left hover:bg-surface-2",
                      selected?.request_id === item.request_id && "bg-accent-soft")}>
                    <span className="truncate text-[15px] font-medium">{item.sender.name} <span className="text-label-2">→</span> {item.recipient.name}</span>
                    <span className="tabular text-right font-semibold">{formatMoney(item.amount)}</span>
                    <span className="tabular truncate text-[12px] text-label-2">{formatTime(item.event_time)} · {item.producer === "manual" ? "simulator" : "stream"}</span>
                    <span className="flex items-center justify-end gap-3">
                      <span className="hidden sm:block"><ComponentMiniBar components={item.components} score={item.risk_score} /></span>
                      <DecisionBadge size="sm" label={item.decision_label} />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <div className="space-y-5 lg:sticky lg:top-6 lg:self-start">
          <Card>
            <CardHeader title="Assessment history" subtitle="Where each action in this feed came from" />
            <div className="px-5 pb-5">
              <KeyValue items={[
                { label: "Anomaly risk policy", value: sources.risk_policy },
                { label: "Confirmed fraud evidence", value: sources.confirmed_fraud_evidence },
                { label: "Assessment safeguard", value: sources.assessment_safeguard },
              ]} />
            </div>
          </Card>
          {selected ? (
            <Card>
              <CardHeader title="Selected assessment" subtitle={`${selected.request_id} · ${formatTime(selected.event_time)}`} />
              <div className="space-y-4 px-5 pb-5">
                <div className="flex flex-wrap items-center gap-2">
                  <DecisionBadge label={selected.decision_label} />
                  <Chip>{SOURCE_TEXT[selected.decision_source]}</Chip>
                </div>
                <p className="text-[14px]">
                  {selected.sender.name} → {selected.recipient.name} · {formatMoney(selected.amount)} · {OUTCOME_TEXT[selected.outcome]}
                </p>
                {selected.corroborating_signals.length ? (
                  <div className="flex flex-wrap gap-1.5">{selected.corroborating_signals.map((f) => <Chip key={f} tone="accent">{FAMILY_TEXT[f] ?? f}</Chip>)}</div>
                ) : null}
                {selected.evidence_ids.length ? <p className="text-[13px] text-label-2">Evidence {selected.evidence_ids.join(", ")}</p> : null}
                {point ? <RiskComposition details={detailsFrom(selected)} total={selected.risk_score} verify={point.verify} block={point.block} /> : null}
                <Link to={`/investigations/${encodeURIComponent(selected.request_id)}`} className="inline-flex items-center gap-1 text-[15px] font-medium text-accent">
                  Open investigation <ArrowRight aria-hidden className="size-4" />
                </Link>
              </div>
            </Card>
          ) : null}
        </div>
      </div>
    </>
  );
}
