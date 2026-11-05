import { SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router";
import { useTransactions } from "../api/hooks";
import { AssessmentRow } from "../components/AssessmentRow";
import { Pagination } from "../components/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { Button, Card, Field, PageHeader, Segmented, inputClass } from "../components/ui";

const FILTER_KEYS = ["q", "decision", "decision_source", "origin", "review_status", "date_from", "date_to", "min_score", "max_score", "sort"] as const;
const ADVANCED = FILTER_KEYS.slice(2);

export function TransactionsPage() {
  const [params, setParams] = useSearchParams();
  const page = Number(params.get("page") ?? "1") || 1;
  const filters: Record<string, string | number | undefined> = { page, page_size: 25 };
  for (const key of FILTER_KEYS) filters[key] = params.get(key) ?? undefined;
  const { data, error, isPending, isFetching, refetch } = useTransactions(filters);

  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete("page");
    setParams(next, { replace: true });
  };
  const hasFilters = FILTER_KEYS.some((k) => params.get(k));
  const [showMore, setShowMore] = useState(
    () => ADVANCED.some((k) => params.get(k)) || (typeof window.matchMedia === "function" && window.matchMedia("(min-width: 768px)").matches),
  );

  return (
    <>
      <PageHeader title="Transactions" subtitle="Every assessed payment request: the demonstration history plus this session's simulations." />
      <Card className="mb-5 space-y-4 p-5">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[240px] flex-1">
            <Field label="Search" htmlFor="tx-search">
              <input
                id="tx-search"
                type="search"
                className={inputClass}
                placeholder="Account name, account ID, or request ID"
                defaultValue={params.get("q") ?? ""}
                onKeyDown={(e) => e.key === "Enter" && update("q", e.currentTarget.value.trim())}
                onBlur={(e) => e.currentTarget.value.trim() !== (params.get("q") ?? "") && update("q", e.currentTarget.value.trim())}
              />
            </Field>
          </div>
          <div>
            <span className="mb-1.5 block text-[13px] font-medium text-label-2">Decision</span>
            <Segmented
              label="Decision"
              value={params.get("decision") ?? ""}
              onChange={(v) => update("decision", v)}
              options={[
                { value: "", label: "All" },
                { value: "Permit", label: "Permit" },
                { value: "Verify", label: "Verify" },
                { value: "Block", label: "Block" },
              ]}
            />
          </div>
        </div>
        <Button variant="plain" aria-expanded={showMore} aria-controls="tx-more" onClick={() => setShowMore((v) => !v)} className="-ml-2">
          <SlidersHorizontal aria-hidden className="size-4" /> {showMore ? "Fewer filters" : "More filters"}
        </Button>
        <div id="tx-more" hidden={!showMore} className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
          <Field label="Decision source" htmlFor="tx-source">
            <select id="tx-source" className={inputClass} value={params.get("decision_source") ?? ""} onChange={(e) => update("decision_source", e.target.value)}>
              <option value="">Any source</option>
              <option value="confirmed_fraud_evidence">Confirmed fraud evidence</option>
              <option value="risk_policy">Anomaly risk policy</option>
              <option value="assessment_safeguard">Assessment safeguard</option>
            </select>
          </Field>
          <Field label="Origin" htmlFor="tx-origin">
            <select id="tx-origin" className={inputClass} value={params.get("origin") ?? ""} onChange={(e) => update("origin", e.target.value)}>
              <option value="">History and simulations</option>
              <option value="baseline">Demonstration history</option>
              <option value="simulation">Simulations</option>
            </select>
          </Field>
          <Field label="Review" htmlFor="tx-review">
            <select id="tx-review" className={inputClass} value={params.get("review_status") ?? ""} onChange={(e) => update("review_status", e.target.value)}>
              <option value="">Any</option>
              <option value="pending">Awaiting review</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </Field>
          <Field label="From" htmlFor="tx-from">
            <input id="tx-from" type="date" className={inputClass} value={params.get("date_from") ?? ""} onChange={(e) => update("date_from", e.target.value)} />
          </Field>
          <Field label="To" htmlFor="tx-to">
            <input id="tx-to" type="date" className={inputClass} value={params.get("date_to") ?? ""} onChange={(e) => update("date_to", e.target.value)} />
          </Field>
          <Field label="Min risk" htmlFor="tx-min">
            <input id="tx-min" type="number" min={0} max={100} inputMode="decimal" className={inputClass} defaultValue={params.get("min_score") ?? ""} onBlur={(e) => update("min_score", e.target.value)} />
          </Field>
          <Field label="Sort" htmlFor="tx-sort">
            <select id="tx-sort" className={inputClass} value={params.get("sort") ?? "time_desc"} onChange={(e) => update("sort", e.target.value === "time_desc" ? "" : e.target.value)}>
              <option value="time_desc">Newest first</option>
              <option value="time_asc">Oldest first</option>
              <option value="risk_desc">Highest risk first</option>
            </select>
          </Field>
        </div>
        {hasFilters ? (
          <Button variant="plain" onClick={() => setParams(new URLSearchParams(), { replace: true })}>Clear filters</Button>
        ) : null}
      </Card>

      <Card aria-busy={isFetching}>
        {isPending ? (
          <LoadingState rows={8} />
        ) : error ? (
          <ErrorState error={error} onRetry={() => void refetch()} />
        ) : data.items.length === 0 ? (
          <EmptyState title="No matching requests">Try a different name, ID, or a wider date and score range.</EmptyState>
        ) : (
          <>
            <ul>{data.items.map((item) => <AssessmentRow key={item.request_id} item={item} />)}</ul>
            <Pagination page={data.page} pageSize={data.page_size} total={data.total} onPage={(p) => {
              const next = new URLSearchParams(params);
              next.set("page", String(p));
              setParams(next);
              window.scrollTo({ top: 0 });
            }} />
          </>
        )}
      </Card>
    </>
  );
}
