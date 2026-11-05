import { ChevronRight } from "lucide-react";
import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { useAccounts } from "../api/hooks";
import { DecisionBadge } from "../components/DecisionBadge";
import { Pagination } from "../components/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { Card, Field, PageHeader, Segmented, inputClass } from "../components/ui";
import type { Decision, DecisionLabel } from "../api/types";
import { formatDateTime, formatInt } from "../lib/format";

const LAST: Record<Decision, DecisionLabel> = { Permit: "Permitted", Verify: "Needs verification", Block: "Preventive risk block" };

export function AccountsPage() {
  const [params, setParams] = useSearchParams();
  const [draft, setDraft] = useState(params.get("q") ?? "");
  const page = Number(params.get("page") ?? "1") || 1;
  const type = params.get("account_type") ?? "";
  const { data, error, isPending, refetch } = useAccounts({ q: params.get("q") ?? undefined, account_type: type || undefined, page, page_size: 30 });

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setParams(next, { replace: key !== "page" });
  };

  return (
    <>
      <PageHeader title="Accounts" subtitle="400 named accounts with their activity, behaviour profile, and context findings. Names are generated identities." />
      <Card className="mb-5 flex flex-wrap items-end gap-3 p-5">
        <form className="min-w-[240px] flex-1" onSubmit={(e) => { e.preventDefault(); set("q", draft.trim()); }} role="search">
          <Field label="Search accounts" htmlFor="acct-search">
            <input id="acct-search" type="search" className={inputClass} placeholder="Name or account ID" value={draft}
              onChange={(e) => { setDraft(e.target.value); if (!e.target.value) set("q", ""); }} />
          </Field>
        </form>
        <Segmented label="Account type" value={type} onChange={(v) => set("account_type", v)}
          options={[{ value: "", label: "All" }, { value: "personal", label: "Personal" }, { value: "business", label: "Business" }]} />
      </Card>
      <Card>
        {isPending ? <LoadingState rows={8} /> : error ? <ErrorState error={error} onRetry={() => void refetch()} /> : data.items.length === 0 ? (
          <EmptyState title="No accounts found">Search by part of a name, for example a surname, or by account ID.</EmptyState>
        ) : (
          <>
            <ul>
              {data.items.map((a) => (
                <li key={a.account_id} className="border-b border-separator last:border-0">
                  <Link to={`/accounts/${a.account_id}`} className="grid grid-cols-[1fr_auto] items-center gap-3 px-5 py-3 hover:bg-surface-2 sm:grid-cols-[minmax(0,1fr)_120px_120px_auto]">
                    <div className="min-w-0">
                      <p className="truncate text-[15px] font-medium">{a.display_name}</p>
                      <p className="text-[12px] text-label-2">{a.account_id} · {a.account_type} · {a.home_country}</p>
                    </div>
                    <div className="tabular hidden text-[13px] text-label-2 sm:block">{formatInt(a.requests)} requests<br />{formatInt(a.flagged)} flagged</div>
                    <div className="hidden text-[12px] text-label-2 sm:block">{a.last_activity ? formatDateTime(a.last_activity) : "No activity"}</div>
                    <div className="flex items-center gap-1">
                      {a.last_decision ? <DecisionBadge size="sm" label={LAST[a.last_decision]} /> : null}
                      <ChevronRight aria-hidden className="size-4 text-label-2" />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
            <Pagination page={data.page} pageSize={data.page_size} total={data.total} onPage={(p) => set("page", String(p))} />
          </>
        )}
      </Card>
    </>
  );
}
