import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

export function Card({
  children,
  className,
  as: Tag = "section",
  ...rest
}: HTMLAttributes<HTMLElement> & { children: ReactNode; className?: string; as?: "section" | "div" | "article" }) {
  return (
    <Tag {...rest} className={cx("rounded-[14px] bg-surface shadow-[0_0_0_1px_var(--sf-separator)]", className)}>
      {children}
    </Tag>
  );
}

export function CardHeader({ title, subtitle, action }: { title: string; subtitle?: ReactNode; action?: ReactNode }) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-3 px-5 pt-4 pb-3">
      <div className="min-w-0">
        <h2 className="text-[17px] font-semibold tracking-[-0.01em]">{title}</h2>
        {subtitle ? <p className="mt-0.5 text-[13px] text-label-2">{subtitle}</p> : null}
      </div>
      {action}
    </header>
  );
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="font-display text-[28px] leading-tight font-bold tracking-[-0.02em] sm:text-[32px]">{title}</h1>
        {subtitle ? <p className="mt-1 max-w-3xl text-[15px] text-label-2">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}

type Variant = "primary" | "secondary" | "plain" | "destructive";

export function Button({ variant = "secondary", className, children, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  const styles: Record<Variant, string> = {
    primary: "bg-accent text-white hover:brightness-110 disabled:opacity-50",
    secondary: "bg-surface-2 text-label hover:bg-surface-3 disabled:opacity-50",
    plain: "text-accent hover:bg-accent-soft disabled:opacity-50",
    destructive: "bg-block text-white hover:brightness-110 disabled:opacity-50",
  };
  return (
    <button
      type="button"
      {...props}
      className={cx(
        "inline-flex min-h-9 items-center justify-center gap-1.5 rounded-[10px] px-3.5 text-[15px] font-medium transition-[filter] disabled:cursor-not-allowed",
        styles[variant],
        className,
      )}
    >
      {children}
    </button>
  );
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
  label,
  size = "md",
  stretch = false,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
  label: string;
  size?: "sm" | "md";
  stretch?: boolean;
}) {
  return (
    <div role="radiogroup" aria-label={label} className={cx("max-w-full overflow-x-auto rounded-[9px] bg-surface-2 p-0.5", stretch ? "flex w-full" : "inline-flex")}>
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(option.value)}
            className={cx(
              "shrink-0 rounded-[7px] font-medium whitespace-nowrap transition-colors",
              stretch && "flex-1",
              size === "sm" ? "min-h-7 px-2.5 text-[13px]" : "min-h-8 px-3 text-[14px]",
              selected ? "bg-surface text-label shadow-[0_1px_3px_rgb(0_0_0/0.12)]" : "text-label-2 hover:text-label",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

export function Stat({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: ReactNode; tone?: "permit" | "verify" | "block" | "evidence" }) {
  const toneClass = tone ? { permit: "text-permit", verify: "text-verify", block: "text-block", evidence: "text-evidence" }[tone] : "text-label";
  return (
    <div className="min-w-0">
      <div className="text-[13px] font-medium text-label-2">{label}</div>
      <div className={cx("tabular mt-1 font-display text-[26px] leading-none font-semibold tracking-[-0.02em]", toneClass)}>{value}</div>
      {hint ? <div className="mt-1.5 text-[12px] text-label-2">{hint}</div> : null}
    </div>
  );
}

export function KeyValue({ items }: { items: { label: string; value: ReactNode }[] }) {
  return (
    <div className="@container">
    <dl className="grid grid-cols-1 gap-x-6 @lg:grid-cols-2">
      {items.map((item) => (
        <div key={item.label} className="flex items-baseline justify-between gap-4 border-b border-separator py-2.5 last:border-0 @lg:[&:nth-last-child(2)]:border-0">
          <dt className="text-[13px] text-label-2">{item.label}</dt>
          <dd className="tabular min-w-0 truncate text-right text-[14px] font-medium">{item.value}</dd>
        </div>
      ))}
    </dl>
    </div>
  );
}

export function Chip({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "accent" | "verify" | "block" | "evidence" | "permit" }) {
  const tones = {
    neutral: "bg-surface-2 text-label-2",
    accent: "bg-accent-soft text-accent",
    verify: "bg-verify-soft text-verify",
    block: "bg-block-soft text-block",
    evidence: "bg-evidence-soft text-evidence",
    permit: "bg-permit-soft text-permit",
  };
  return <span className={cx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[12px] font-medium", tones[tone])}>{children}</span>;
}

export const inputClass =
  "min-h-10 w-full rounded-[10px] border border-separator bg-surface px-3 text-[15px] text-label placeholder:text-label-2 focus:border-accent focus:outline-none focus-visible:outline-2 focus-visible:outline-accent";

export function Field({ label, hint, error, children, htmlFor }: { label: string; hint?: string; error?: string; children: ReactNode; htmlFor: string }) {
  return (
    <div className="min-w-0">
      <label htmlFor={htmlFor} className="mb-1.5 block text-[13px] font-medium text-label-2">
        {label}
      </label>
      {children}
      {error ? (
        <p role="alert" className="mt-1 text-[13px] text-block">
          {error}
        </p>
      ) : hint ? (
        <p className="mt-1 text-[12px] text-label-2">{hint}</p>
      ) : null}
    </div>
  );
}
