import { ChevronRight } from "lucide-react";
import { Link } from "react-router";
import type { AssessmentSummary } from "../api/types";
import { formatDateTime, formatMoney } from "../lib/format";
import { DecisionBadge } from "./DecisionBadge";
import { ComponentMiniBar } from "./RiskComposition";
import { cx } from "./ui";

/** Two-line list row: who and how much first, then when, risk, and decision. Names lead; IDs are secondary. */
export function AssessmentRow({ item, highlight, compact }: { item: AssessmentSummary; highlight?: boolean; compact?: boolean }) {
  const reviewed =
    item.review_status === "approved" ? " · approved after review" : item.review_status === "rejected" ? " · rejected after review" : "";
  return (
    <li className={cx("border-b border-separator last:border-0", highlight && "sf-arrive")}>
      <Link
        to={`/investigations/${encodeURIComponent(item.request_id)}`}
        className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 px-5 py-3 hover:bg-surface-2"
      >
        <p className="truncate text-[15px] font-medium">
          {item.sender.name} <span className="text-label-2">→</span> {item.recipient.name}
        </p>
        <p className="tabular text-right text-[15px] font-semibold">{formatMoney(item.amount)}</p>
        <p className="tabular truncate text-[12px] text-label-2">
          {formatDateTime(item.event_time)}
          {compact ? "" : ` · ${item.request_id}`}
          {reviewed}
        </p>
        <div className="flex items-center justify-end gap-3">
          {!compact ? (
            <span className="hidden sm:block">
              <ComponentMiniBar components={item.components} score={item.risk_score} />
            </span>
          ) : null}
          <span className="flex items-center gap-1">
            <DecisionBadge label={item.decision_label} size="sm" />
            <ChevronRight aria-hidden className="size-4 text-label-2" />
          </span>
        </div>
      </Link>
    </li>
  );
}
