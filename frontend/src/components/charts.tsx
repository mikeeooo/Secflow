import { useId, useState } from "react";
import { cx } from "./ui";

export interface Series {
  key: string;
  label: string;
  swatch: string; // tailwind bg-* class
}

export interface Column {
  label: string;
  values: Record<string, number>;
}

function niceMax(value: number): number {
  if (value <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 2.5, 5, 10].find((m) => m * magnitude >= value) ?? 10;
  return step * magnitude;
}

/** Stacked (or single) columns in HTML so text never scales with the plot. Hover shows exact values. */
export function ColumnChart({
  title,
  columns,
  series,
  height = 160,
  valueFormat = (v: number) => v.toLocaleString("en-IE"),
  xLabels,
}: {
  title: string;
  columns: Column[];
  series: Series[];
  height?: number;
  valueFormat?: (value: number) => string;
  xLabels?: [string, string];
}) {
  const [hover, setHover] = useState<number | null>(null);
  const totals = columns.map((c) => series.reduce((sum, s) => sum + (c.values[s.key] ?? 0), 0));
  const max = niceMax(Math.max(0, ...totals));
  const tableId = useId();
  const active = hover == null ? null : columns[hover];
  return (
    <figure className="m-0">
      <figcaption className="sr-only">{title}</figcaption>
      {series.length > 1 ? (
        <ul className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-label-2">
          {series.map((s) => (
            <li key={s.key} className="flex items-center gap-1.5">
              <span aria-hidden className={cx("size-2.5 rounded-sm", s.swatch)} />
              {s.label}
            </li>
          ))}
        </ul>
      ) : null}
      <div className="relative">
        <div className="tabular absolute top-0 left-0 text-[11px] text-label-2">{valueFormat(max)}</div>
        <div
          className="flex items-end overflow-hidden border-b border-separator pt-4"
          style={{ height, gap: columns.length > 60 ? 1 : 2 }}
          onMouseLeave={() => setHover(null)}
          aria-describedby={tableId}
        >
          {columns.map((column, i) => (
            <div
              key={column.label}
              className="relative flex h-full min-w-0 flex-1 cursor-default flex-col justify-end"
              onMouseEnter={() => setHover(i)}
            >
              <div className={cx("flex flex-col-reverse gap-[2px]", hover === i && "opacity-80")}>
                {series.map((s, si) => {
                  const value = column.values[s.key] ?? 0;
                  if (!value) return null;
                  const isTop = series.slice(si + 1).every((x) => !(column.values[x.key] ?? 0));
                  return (
                    <div
                      key={s.key}
                      className={cx(s.swatch, isTop && "rounded-t-[4px]")}
                      style={{ height: Math.max(1, (value / max) * (height - 16)) }}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        {active ? (
          <div
            role="status"
            className="pointer-events-none absolute -top-2 z-10 min-w-36 -translate-x-1/2 rounded-[10px] bg-surface px-3 py-2 text-[12px] shadow-lg ring-1 ring-separator"
            style={{ left: `${((hover! + 0.5) / columns.length) * 100}%` }}
          >
            <div className="font-semibold">{active.label}</div>
            {series.map((s) => (
              <div key={s.key} className="tabular flex items-center justify-between gap-3">
                <span className="flex items-center gap-1.5 text-label-2">
                  <span aria-hidden className={cx("size-2 rounded-sm", s.swatch)} />
                  {s.label}
                </span>
                <span className="font-medium">{valueFormat(active.values[s.key] ?? 0)}</span>
              </div>
            ))}
          </div>
        ) : null}
        {xLabels ? (
          <div className="mt-1.5 flex justify-between text-[11px] text-label-2">
            <span>{xLabels[0]}</span>
            <span>{xLabels[1]}</span>
          </div>
        ) : null}
      </div>
      <details id={tableId} className="mt-2 text-[12px] text-label-2">
        <summary className="cursor-pointer select-none">View data table</summary>
        <div className="mt-2 max-h-48 overflow-auto">
          <table className="tabular w-full text-left">
            <thead>
              <tr>
                <th className="py-1 pr-3 font-medium">Bucket</th>
                {series.map((s) => (
                  <th key={s.key} className="py-1 pr-3 font-medium">{s.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {columns.map((c) => (
                <tr key={c.label} className="border-t border-separator">
                  <td className="py-1 pr-3">{c.label}</td>
                  {series.map((s) => (
                    <td key={s.key} className="py-1 pr-3">{valueFormat(c.values[s.key] ?? 0)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}

/** Single-series line with a hover crosshair. One y-axis only. */
export function LineChart({
  title,
  points,
  height = 140,
  yMax,
  valueFormat = (v: number) => v.toFixed(1),
  xLabels,
}: {
  title: string;
  points: { label: string; value: number | null }[];
  height?: number;
  yMax?: number;
  valueFormat?: (value: number) => string;
  xLabels?: [string, string];
}) {
  const [hover, setHover] = useState<number | null>(null);
  const values = points.map((p) => p.value).filter((v): v is number => v != null);
  const max = yMax ?? niceMax(Math.max(1, ...values));
  const n = Math.max(1, points.length - 1);
  const path = points
    .map((p, i) => (p.value == null ? null : `${(i / n) * 100},${100 - (p.value / max) * 100}`))
    .filter(Boolean)
    .join(" ");
  const active = hover == null ? null : points[hover];
  return (
    <figure className="m-0">
      <figcaption className="sr-only">{title}</figcaption>
      <div className="relative" style={{ height }}>
        <div className="tabular absolute top-0 left-0 text-[11px] text-label-2">{valueFormat(max)}</div>
        <svg
          className="absolute inset-x-0 top-4 bottom-0 h-[calc(100%-16px)] w-full overflow-visible"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          role="img"
          aria-label={`${title}: ${values.length} points, latest ${values.length ? valueFormat(values[values.length - 1]) : "none"}`}
          onMouseMove={(event) => {
            const rect = event.currentTarget.getBoundingClientRect();
            setHover(Math.round(((event.clientX - rect.left) / rect.width) * n));
          }}
          onMouseLeave={() => setHover(null)}
        >
          <line x1="0" x2="100" y1="100" y2="100" stroke="var(--sf-separator)" vectorEffect="non-scaling-stroke" />
          <polyline points={path} fill="none" stroke="var(--sf-accent)" strokeWidth="2" vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
          {hover != null ? (
            <line x1={(hover / n) * 100} x2={(hover / n) * 100} y1="0" y2="100" stroke="var(--sf-label-2)" strokeDasharray="2 2" vectorEffect="non-scaling-stroke" />
          ) : null}
        </svg>
        {active ? (
          <div
            role="status"
            className="pointer-events-none absolute -top-2 z-10 -translate-x-1/2 rounded-[10px] bg-surface px-3 py-2 text-[12px] whitespace-nowrap shadow-lg ring-1 ring-separator"
            style={{ left: `${(hover! / n) * 100}%` }}
          >
            <div className="font-semibold">{active.label}</div>
            <div className="tabular">{active.value == null ? "No data" : valueFormat(active.value)}</div>
          </div>
        ) : null}
      </div>
      {xLabels ? (
        <div className="mt-1.5 flex justify-between text-[11px] text-label-2">
          <span>{xLabels[0]}</span>
          <span>{xLabels[1]}</span>
        </div>
      ) : null}
    </figure>
  );
}

/** Part-to-whole bar for the four decision outcomes, always with a labelled legend. */
export function ShareBar({ parts }: { parts: { key: string; label: string; value: number; swatch: string }[] }) {
  const total = parts.reduce((sum, p) => sum + p.value, 0) || 1;
  return (
    <div>
      <div
        role="img"
        aria-label={parts.map((p) => `${p.label} ${p.value}`).join(", ")}
        className="flex h-3 gap-[2px] overflow-hidden rounded-full"
      >
        {parts.map((p) => (p.value ? <div key={p.key} className={p.swatch} style={{ width: `${(p.value / total) * 100}%`, minWidth: 3 }} /> : null))}
      </div>
      <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2">
        {parts.map((p) => (
          <li key={p.key} className="min-w-0 text-[13px]">
            <div className="flex items-start gap-1.5 leading-tight text-label-2">
              <span aria-hidden className={cx("mt-0.5 size-2.5 shrink-0 rounded-sm", p.swatch)} />
              <span>{p.label}</span>
            </div>
            <div className="tabular font-semibold">
              {p.value.toLocaleString("en-IE")} <span className="font-normal text-label-2">· {((p.value / total) * 100).toFixed(1)}%</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
