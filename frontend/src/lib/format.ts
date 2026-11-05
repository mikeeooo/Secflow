import type { DecisionLabel, DecisionSource, Outcome } from "../api/types";

const money = new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR", minimumFractionDigits: 2 });
const compactMoney = new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR", notation: "compact", maximumFractionDigits: 1 });
const integer = new Intl.NumberFormat("en-IE");

export const formatMoney = (value: number | null | undefined): string => (value == null ? "—" : money.format(value));
export const formatCompactMoney = (value: number): string => compactMoney.format(value);
export const formatInt = (value: number | null | undefined): string => (value == null ? "—" : integer.format(value));

export function formatPercent(value: number | null | undefined, digits = 1): string {
  return value == null ? "n/a" : `${(value * 100).toFixed(digits)}%`;
}

export function formatScore(value: number | null | undefined): string {
  return value == null ? "—" : value.toFixed(1);
}

/** Simulation and dataset times are shown in UTC so that every view agrees. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  return `${date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })}, ${date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "UTC" })} UTC`;
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "UTC" });
}

export function formatDay(iso: string): string {
  return new Date(`${iso.slice(0, 10)}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
}

export const SOURCE_TEXT: Record<DecisionSource, string> = {
  confirmed_fraud_evidence: "Confirmed fraud evidence",
  risk_policy: "Anomaly risk policy",
  assessment_safeguard: "Assessment safeguard",
};

export const OUTCOME_TEXT: Record<Outcome, string> = {
  permitted: "Recorded as permitted",
  pending_verification: "Awaiting verification",
  blocked_attempt: "Blocked attempt",
  approved_after_review: "Approved after review",
  rejected_after_review: "Rejected after review",
};

export const LABEL_HINT: Record<DecisionLabel, string> = {
  "Confirmed fraud evidence": "Blocked because trusted security evidence was active at request time.",
  "Preventive risk block": "Blocked by the validated risk policy with corroborating behaviour; not confirmed fraud.",
  "Needs verification": "Held until an analyst approves or rejects it.",
  Permitted: "Below the verification threshold with no active evidence.",
};

export const FAMILY_TEXT: Record<string, string> = {
  velocity: "Velocity",
  amount_deviation: "Amount deviation",
  compromised_access: "Device & sign-in",
  beneficiary_risk: "Beneficiary network",
  funds_flow: "Pass-through funds",
};

export function humanize(value: string): string {
  const text = value.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function newRequestId(): string {
  const random = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID().replace(/-/g, "").slice(0, 16)
    : Math.random().toString(36).slice(2, 18);
  return `SIM-${random}`;
}
