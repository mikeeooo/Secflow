import { useId, useState, type ReactNode } from "react";
import { cx } from "./ui";

/* Grafana-style monitoring panels. Colours come from CSS variables so light and dark both work. */

export function Panel({ title, children, info, className }: { title: string; children: ReactNode; info?: ReactNode; className?: string }) {
  return (
    <section className={cx("flex min-w-0 flex-col rounded-[10px] bg-surface shadow-[0_0_0_1px_var(--sf-separator)]", className)}>
      <header className="flex items-center justify-between gap-2 px-4 pt-3 pb-1">
        <h3 className="truncate text-[14px] font-semibold">{title}</h3>
        {info ? <span className="shrink-0 text-[12px] text-label-2">{info}</span> : null}
      </header>
      <div className="min-h-0 flex-1 px-4 pb-3">{children}</div>
    </section>
  );
}

export interface LineSeries {
  key: string;
  label: string;
  color: string; // CSS colour, e.g. "var(--sf-if)"
  opacity?: number;
  fill?: boolean;
}

export interface ReferenceLine {
  value: number;
  label: string;
  color: string;
}

type Point = { t: string; values: Record<string, number | null> };

function stats(values: (number | null)[]) {
  const present = values.filter((v): v is number => v != null);
  if (!present.length) return { mean: null, max: null, last: null };
  return {
    mean: present.reduce((a, b) => a + b, 0) / present.length,
    max: Math.max(...present),
    last: present[present.length - 1],
  };
}

/** Multi-series time series on one y-axis with crosshair tooltip and a Grafana-like legend table. */
export function TimeSeries({
  title,
  points,
  series,
  yMax,
  yFormat = (v) => v.toFixed(2),
  xFormat,
  height = 190,
  references = [],
}: {
  title: string;
  points: Point[];
  series: LineSeries[];
  yMax?: number;
  yFormat?: (value: number) => string;
  xFormat: (iso: string) => string;
  height?: number;
  references?: ReferenceLine[];
}) {
  const [hover, setHover] = useState<number | null>(null);
  const gradientId = useId().replace(/:/g, "");
  const all = points.flatMap((p) => series.map((s) => p.values[s.key])).filter((v): v is number => v != null);
  const max = yMax ?? Math.max(1e-9, ...all, ...references.map((r) => r.value)) * 1.1;
  const n = Math.max(1, points.length - 1);
  const x = (i: number) => (i / n) * 100;
  const y = (v: number) => 100 - (v / max) * 100;
  const pathFor = (key: string) => {
    let d = "";
    let open = false;
    points.forEach((p, i) => {
      const v = p.values[key];
      if (v == null) {
        open = false;
        return;
      }
      d += `${open ? "L" : "M"}${x(i)},${y(v)}`;
      open = true;
    });
    return d;
  };
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * max);
  const labelIdx = points.length > 1 ? [0, Math.floor(n / 4), Math.floor(n / 2), Math.floor((3 * n) / 4), n] : [0];
  const active = hover == null ? null : points[hover];
  return (
    <figure className="m-0">
      <figcaption className="sr-only">{title}</figcaption>
      <div className="relative pl-10" style={{ height }}>
        {ticks.map((t) => (
          <span key={t} className="tabular absolute left-0 -translate-y-1/2 text-[10px] text-label-2" style={{ top: `${100 - (t / max) * 100}%` }}>
            {yFormat(t)}
          </span>
        ))}
        <svg
          className="h-full w-full overflow-visible"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          role="img"
          aria-label={`${title}. ${series.map((s) => {
            const st = stats(points.map((p) => p.values[s.key]));
            return `${s.label}: mean ${st.mean == null ? "n/a" : yFormat(st.mean)}`;
          }).join("; ")}`}
          onMouseMove={(event) => {
            const rect = event.currentTarget.getBoundingClientRect();
            setHover(Math.max(0, Math.min(n, Math.round(((event.clientX - rect.left) / rect.width) * n))));
          }}
          onMouseLeave={() => setHover(null)}
        >
          <defs>
            {series.map((s) => (
              <linearGradient key={s.key} id={`${gradientId}-${s.key}`} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={s.color} stopOpacity={0.28} />
                <stop offset="100%" stopColor={s.color} stopOpacity={0.02} />
              </linearGradient>
            ))}
          </defs>
          {ticks.map((t) => (
            <line key={t} x1="0" x2="100" y1={y(t)} y2={y(t)} stroke="var(--sf-separator)" vectorEffect="non-scaling-stroke" />
          ))}
          {series.map((s) =>
            s.fill ? (
              <path key={`f-${s.key}`} d={`${pathFor(s.key)}L100,100L0,100Z`} fill={`url(#${gradientId}-${s.key})`} stroke="none" />
            ) : null,
          )}
          {references.map((r) => (
            <line key={r.label} x1="0" x2="100" y1={y(r.value)} y2={y(r.value)} stroke={r.color} strokeDasharray="4 3" vectorEffect="non-scaling-stroke" />
          ))}
          {series.map((s) => (
            <path key={s.key} d={pathFor(s.key)} fill="none" stroke={s.color} strokeOpacity={s.opacity ?? 1} strokeWidth="2" vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
          ))}
          {hover != null ? (
            <line x1={x(hover)} x2={x(hover)} y1="0" y2="100" stroke="var(--sf-label-2)" strokeDasharray="2 2" vectorEffect="non-scaling-stroke" />
          ) : null}
        </svg>
        {references.map((r) => (
          <span key={r.label} className="tabular absolute right-0 -translate-y-full text-[10px] font-semibold" style={{ top: `${y(r.value)}%`, color: r.color }}>
            {r.label}
          </span>
        ))}
        {active ? (
          <div
            role="status"
            className="pointer-events-none absolute top-0 z-10 min-w-40 rounded-[8px] bg-surface px-3 py-2 text-[12px] shadow-lg ring-1 ring-separator"
            style={hover! > n / 2 ? { right: `${100 - x(hover!)}%` } : { left: `calc(${x(hover!)}% + 2.5rem)` }}
          >
            <div className="mb-1 font-semibold">{xFormat(active.t)}</div>
            {series.map((s) => (
              <div key={s.key} className="tabular flex items-center justify-between gap-4">
                <span className="flex items-center gap-1.5 text-label-2">
                  <span aria-hidden className="h-0.5 w-3 rounded" style={{ background: s.color, opacity: s.opacity ?? 1 }} />
                  {s.label}
                </span>
                <span className="font-medium">{active.values[s.key] == null ? "—" : yFormat(active.values[s.key]!)}</span>
              </div>
            ))}
          </div>
        ) : null}
      </div>
      <div className="mt-1 flex justify-between pl-10 text-[10px] text-label-2">
        {labelIdx.map((i) => (
          <span key={i}>{points[i] ? xFormat(points[i].t) : ""}</span>
        ))}
      </div>
      <table className="tabular mt-2 w-full text-[12px]">
        <thead className="text-label-2">
          <tr>
            <th className="text-left font-normal"><span className="sr-only">Series</span></th>
            <th className="w-16 text-right font-medium">Mean</th>
            <th className="w-16 text-right font-medium">Max</th>
            <th className="w-16 text-right font-medium">Last</th>
          </tr>
        </thead>
        <tbody>
          {series.map((s) => {
            const st = stats(points.map((p) => p.values[s.key]));
            const show = (v: number | null) => (v == null ? "—" : yFormat(v));
            return (
              <tr key={s.key}>
                <td className="py-0.5">
                  <span className="flex items-center gap-1.5">
                    <span aria-hidden className="h-1 w-3.5 rounded" style={{ background: s.color, opacity: s.opacity ?? 1 }} />
                    {s.label}
                  </span>
                </td>
                <td className="text-right">{show(st.mean)}</td>
                <td className="text-right">{show(st.max)}</td>
                <td className="text-right">{show(st.last)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </figure>
  );
}

export interface GaugeBand {
  to: number;
  color: string;
}

const ARC_START = -225; // degrees, measured clockwise from 3 o'clock
const ARC_SWEEP = 270;

function polar(angle: number, radius: number) {
  const rad = (angle * Math.PI) / 180;
  return { x: 60 + radius * Math.cos(rad), y: 60 + radius * Math.sin(rad) };
}

function arc(from: number, to: number, radius: number) {
  const a = polar(from, radius);
  const b = polar(to, radius);
  const large = to - from > 180 ? 1 : 0;
  return `M${a.x},${a.y}A${radius},${radius} 0 ${large} 1 ${b.x},${b.y}`;
}

/** Grafana-style gauge: threshold bands on the outer ring, value arc coloured by its band. */
export function Gauge({ value, max, bands, format, label, caption }: { value: number | null; max: number; bands: GaugeBand[]; format: (v: number) => string; label: string; caption?: string }) {
  const clamped = value == null ? 0 : Math.max(0, Math.min(max, value));
  const angle = (v: number) => ARC_START + (v / max) * ARC_SWEEP;
  const band = bands.find((b) => clamped <= b.to) ?? bands[bands.length - 1];
  let start = 0;
  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 120 104" className="w-full max-w-[190px]" role="img" aria-label={`${label}: ${value == null ? "no data" : format(value)}`}>
        <path d={arc(ARC_START, ARC_START + ARC_SWEEP, 44)} fill="none" stroke="var(--sf-surface-2)" strokeWidth="10" strokeLinecap="round" />
        {bands.map((b) => {
          const from = angle(start);
          const to = angle(Math.min(b.to, max));
          start = Math.min(b.to, max);
          return to > from ? <path key={b.to} d={arc(from, to, 53)} fill="none" stroke={b.color} strokeWidth="2.5" /> : null;
        })}
        {value != null && clamped > 0 ? (
          <path d={arc(ARC_START, angle(clamped), 44)} fill="none" stroke={band.color} strokeWidth="10" strokeLinecap="round" />
        ) : null}
        <text x="60" y="66" textAnchor="middle" className="tabular" fontSize="19" fontWeight="600" fill={value == null ? "var(--sf-label-2)" : band.color}>
          {value == null ? "—" : format(value)}
        </text>
      </svg>
      {caption ? <p className="-mt-2 text-center text-[11px] text-label-2">{caption}</p> : null}
    </div>
  );
}

/** Big number with a sparkline underneath, like a Grafana stat panel. */
export function Stat({ value, color, spark, caption }: { value: string; color: string; spark: (number | null)[]; caption?: string }) {
  // Scale to the series' own range (like Grafana) so steady traffic still shows its variation.
  const present = spark.map((v) => v ?? 0);
  const max = Math.max(...present, 0);
  const min = Math.min(...present, max);
  const span = Math.max(1e-9, max - min);
  const n = Math.max(1, present.length - 1);
  const line = present.map((v, i) => `${i ? "L" : "M"}${(i / n) * 100},${95 - ((v - min) / span) * 85}`).join("");
  return (
    <div className="relative flex h-full min-h-[118px] flex-col justify-center">
      <svg className="absolute inset-x-0 bottom-0 h-1/2 w-full" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden>
        <path d={`${line}L100,100L0,100Z`} fill={color} fillOpacity="0.14" />
        <path d={line} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="tabular relative text-center font-display text-[34px] leading-none font-semibold" style={{ color }}>{value}</div>
      {caption ? <p className="relative mt-1 text-center text-[11px] text-label-2">{caption}</p> : null}
    </div>
  );
}

/** Vertical bar gauge with the value printed above each bar. */
export function BarGauge({ items, format, color }: { items: { label: string; value: number; hint?: string }[]; format: (v: number) => string; color: string }) {
  const max = Math.max(1e-9, ...items.map((i) => i.value));
  if (!items.length) return <p className="py-10 text-center text-[13px] text-label-2">No rules triggered in this window.</p>;
  return (
    <ul className="flex h-[230px] items-stretch gap-2" aria-label="Rule trigger counts">
      {items.map((item) => (
        <li key={item.label} className="flex min-w-0 flex-1 flex-col items-center" title={item.hint}>
          <span className="tabular text-[15px] font-semibold" style={{ color }}>{format(item.value)}</span>
          <div className="relative mt-1 w-full flex-1 rounded-[4px] bg-surface-2">
            <div className="absolute inset-x-0 bottom-0 rounded-[4px] border-t-2" style={{ height: `${(item.value / max) * 100}%`, background: `color-mix(in srgb, ${color} 35%, transparent)`, borderColor: color }} />
          </div>
          <span className="mt-1.5 line-clamp-2 h-7 w-full text-center text-[10px] leading-tight text-label-2" title={item.hint ?? item.label}>{item.label}</span>
        </li>
      ))}
    </ul>
  );
}
