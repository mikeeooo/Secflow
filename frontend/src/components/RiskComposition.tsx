import type { ComponentBrief, ComponentKey, ComponentView } from "../api/types";
import { formatScore } from "../lib/format";
import { cx } from "./ui";

export const COMPONENTS: { key: ComponentKey; short: string; label: string; weight: number; swatch: string }[] = [
  { key: "isolation_forest", short: "IF", label: "Isolation Forest", weight: 0.35, swatch: "bg-c-if" },
  { key: "lof", short: "LOF", label: "Local Outlier Factor", weight: 0.25, swatch: "bg-c-lof" },
  { key: "dbscan", short: "DBSCAN", label: "DBSCAN context", weight: 0.1, swatch: "bg-c-dbscan" },
  { key: "rules", short: "Rules", label: "Behaviour rules", weight: 0.3, swatch: "bg-c-rules" },
];

function contributions(components: ComponentBrief): { key: ComponentKey; value: number }[] {
  return COMPONENTS.map((c) => ({ key: c.key, value: 100 * c.weight * (components[c.key] ?? 0) }));
}

/**
 * The signature element: the 0–100 anomaly-risk index drawn as the sum of its weighted parts,
 * with the validated Verify and Block thresholds marked on the same scale.
 */
export function RiskComposition({
  details,
  total,
  verify,
  block,
}: {
  details: ComponentView[];
  total: number | null;
  verify: number;
  block: number;
}) {
  const parts = COMPONENTS.map((c) => {
    const detail = details.find((d) => d.key === c.key);
    return { ...c, score: detail?.score ?? null, contribution: detail?.contribution ?? null };
  });
  const summary =
    total == null
      ? "No risk score: the models are unavailable."
      : `Risk ${formatScore(total)} of 100: ${parts.map((p) => `${p.label} ${formatScore(p.contribution)}`).join(", ")}. Verify at ${verify}, block at ${block}.`;
  return (
    <figure className="@container m-0">
      <div className="flex items-baseline justify-between gap-3">
        <figcaption className="text-[13px] font-medium text-label-2">Anomaly-risk index</figcaption>
        <div className="tabular font-display text-[34px] leading-none font-bold tracking-[-0.02em]">
          {formatScore(total)}
          <span className="ml-1 text-[15px] font-medium text-label-2">/ 100</span>
        </div>
      </div>
      <div role="img" aria-label={summary} className="relative mt-4 mb-7">
        <div className="flex h-4 overflow-hidden rounded-full bg-surface-2">
          {parts.map((p) =>
            p.contribution ? (
              <div key={p.key} className={cx(p.swatch, "h-full border-r border-surface last:border-0")} style={{ width: `${p.contribution}%` }} />
            ) : null,
          )}
        </div>
        <Marker at={verify} label={`Verify ${verify}`} tone="text-verify" border="border-verify" />
        <Marker at={block} label={`Block ${block}`} tone="text-block" border="border-block" align={block > 85 ? "right" : "center"} />
      </div>
      <ul className="grid grid-cols-2 gap-x-4 gap-y-3 @lg:grid-cols-4">
        {parts.map((p) => (
          <li key={p.key} className="min-w-0">
            <div className="flex items-center gap-1.5 text-[13px] font-medium">
              <span aria-hidden className={cx("size-2.5 shrink-0 rounded-sm", p.swatch)} />
              <span className="truncate">{p.label}</span>
            </div>
            <div className="tabular mt-0.5 text-[13px] text-label-2">
              {p.weight.toFixed(2)} × {p.score == null ? "—" : p.score.toFixed(2)} ={" "}
              <span className="font-semibold text-label">{formatScore(p.contribution)}</span>
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-[12px] text-label-2">
        A relative anomaly index, not a probability of fraud. Each model score is the share of reference-period requests
        it ranks as less unusual.
      </p>
    </figure>
  );
}

function Marker({ at, label, tone, border, align = "center" }: { at: number; label: string; tone: string; border: string; align?: "center" | "right" }) {
  return (
    <div aria-hidden className="absolute top-[-4px] bottom-[-4px]" style={{ left: `${at}%` }}>
      <div className={cx("h-6 border-l-2", border)} />
      <div
        className={cx(
          "tabular absolute top-6 text-[11px] font-semibold whitespace-nowrap",
          tone,
          align === "right" ? "right-0" : "-translate-x-1/2",
        )}
      >
        {label}
      </div>
    </div>
  );
}

/** Compact four-part bar for tables and feeds. */
export function ComponentMiniBar({ components, score }: { components: ComponentBrief; score: number | null }) {
  const parts = contributions(components);
  const label =
    score == null
      ? "Risk score unavailable"
      : `Risk ${formatScore(score)}: ${COMPONENTS.map((c, i) => `${c.short} ${parts[i].value.toFixed(1)}`).join(", ")}`;
  return (
    <div className="flex items-center gap-2" title={label}>
      <span className="tabular w-9 text-right text-[14px] font-semibold">{formatScore(score)}</span>
      <div role="img" aria-label={label} className="flex h-1.5 w-16 overflow-hidden rounded-full bg-surface-2">
        {parts.map((p, i) => (p.value > 0 ? <div key={p.key} className={COMPONENTS[i].swatch} style={{ width: `${p.value}%` }} /> : null))}
      </div>
    </div>
  );
}
