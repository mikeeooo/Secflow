import { ArrowRight, RotateCw } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { ApiError, api } from "../api/client";
import { useSimulate, useSimulatorOptions } from "../api/hooks";
import type { AssessmentDetail, AuthMethod, PartyOption, SimulationRequest } from "../api/types";
import { DecisionBadge } from "../components/DecisionBadge";
import { PartyPicker } from "../components/PartyPicker";
import { RiskComposition } from "../components/RiskComposition";
import { errorMessage } from "../components/States";
import { Button, Card, CardHeader, Chip, Field, PageHeader, Segmented, cx, inputClass } from "../components/ui";
import { SOURCE_TEXT, formatDateTime, formatMoney, humanize, newRequestId } from "../lib/format";

type RecipientMode = "existing" | "new";
const NEW_DEVICE = "__new__";
const NEW_NAMES = ["Jordan Pike", "Mara Ellison", "Tobias Renn", "Quinn Albrecht", "Nadia Sorel"];

interface FormState {
  sender: PartyOption | null;
  recipientMode: RecipientMode;
  recipient: PartyOption | null;
  newName: string;
  amount: string;
  device: string;
  auth: AuthMethod;
  failures: number;
  country: string;
}

const EMPTY: FormState = {
  sender: null,
  recipientMode: "existing",
  recipient: null,
  newName: "",
  amount: "",
  device: "",
  auth: "biometric",
  failures: 0,
  country: "",
};

type Errors = Partial<Record<"sender" | "recipient" | "amount" | "form", string>>;

function validate(form: FormState): Errors {
  const errors: Errors = {};
  if (!form.sender) errors.sender = "Choose who is paying.";
  if (form.recipientMode === "existing" && !form.recipient) errors.recipient = "Choose a recipient, or switch to a new recipient.";
  if (form.recipientMode === "new" && form.newName.trim().length < 2) errors.recipient = "Enter the new recipient's name.";
  if (form.recipient && form.sender && form.recipient.id === form.sender.id) errors.recipient = "Sender and recipient must differ.";
  const amount = Number(form.amount);
  if (!form.amount || !Number.isFinite(amount) || amount <= 0) errors.amount = "Enter an amount greater than zero.";
  else if (amount > 1_000_000) errors.amount = "The simulator accepts up to €1,000,000.";
  return errors;
}

export function SimulatorPage() {
  const [form, setForm] = useState<FormState>(EMPTY);
  const [errors, setErrors] = useState<Errors>({});
  const [requestId, setRequestId] = useState(newRequestId);
  const [failedAttempt, setFailedAttempt] = useState(false);
  const [result, setResult] = useState<AssessmentDetail | null>(null);
  const options = useSimulatorOptions(form.sender?.id);
  const simulate = useSimulate();
  const sender = options.data?.sender;

  // Start with a named sender so presets work immediately.
  useEffect(() => {
    let cancelled = false;
    api.parties("", 1).then((found) => {
      if (!cancelled && found[0]) setForm((f) => (f.sender ? f : { ...f, sender: found[0] }));
    }).catch(() => undefined);
    return () => { cancelled = true; };
  }, []);

  // Default the device and session country to the sender's observed values.
  useEffect(() => {
    if (!sender) return;
    setForm((f) => ({
      ...f,
      device: f.device && (f.device === NEW_DEVICE || sender.known_devices.includes(f.device)) ? f.device : sender.known_devices[0] ?? NEW_DEVICE,
      country: f.country || sender.home_country,
    }));
  }, [sender]);

  const change = (patch: Partial<FormState>) => {
    setForm((f) => ({ ...f, ...patch }));
    if (failedAttempt) { // a changed payload is a new request, not a retry
      setRequestId(newRequestId());
      setFailedAttempt(false);
    }
  };

  const median = sender?.median_amount ?? 50;
  const presets = useMemo(() => {
    const known = sender?.recent_recipients ?? [];
    const flagged = options.data?.flagged_beneficiaries ?? [];
    const device = sender?.known_devices[0] ?? NEW_DEVICE;
    const home = sender?.home_country ?? "DE";
    const name = NEW_NAMES[(form.sender?.id.charCodeAt(form.sender.id.length - 1) ?? 0) % NEW_NAMES.length];
    return [
      {
        id: "ordinary", label: "Ordinary payment", hint: "Usual amount to a recent recipient, known device",
        apply: (): Partial<FormState> => ({ recipientMode: "existing", recipient: known[0] ? { ...known[0], detail: "" } : null, amount: (median * 0.9).toFixed(2), device, auth: "biometric", failures: 0, country: home }),
      },
      {
        id: "verify", label: "Unusual but plausible", hint: "Larger first payment to someone new, known device",
        apply: (): Partial<FormState> => ({ recipientMode: "new", newName: name, recipient: null, amount: (median * 7).toFixed(2), device, auth: "password", failures: 0, country: home }),
      },
      {
        id: "high", label: "High-risk pattern", hint: "New device after failed sign-ins, abroad, large amount",
        apply: (): Partial<FormState> => ({ recipientMode: "new", newName: name, recipient: null, amount: (median * 14).toFixed(2), device: NEW_DEVICE, auth: "password", failures: 3, country: home === "US" ? "GB" : "US" }),
      },
      {
        id: "flagged", label: "Flagged beneficiary", hint: flagged.length ? "Ordinary payment to a beneficiary with active security evidence" : "No beneficiary currently has active evidence",
        disabled: flagged.length === 0,
        apply: (): Partial<FormState> => ({ recipientMode: "existing", recipient: flagged[0] ? { id: flagged[0].id, name: flagged[0].name, kind: "counterparty", detail: "" } : null, amount: (median * 0.8).toFixed(2), device, auth: "biometric", failures: 0, country: home }),
      },
    ];
  }, [sender, options.data, median, form.sender]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length || simulate.isPending || !form.sender) return;
    const body: SimulationRequest = {
      request_id: requestId,
      sender_id: form.sender.id,
      recipient_id: form.recipientMode === "existing" ? form.recipient?.id : null,
      new_recipient_name: form.recipientMode === "new" ? form.newName.trim() : null,
      amount: Number(Number(form.amount).toFixed(2)),
      currency: "EUR",
      device_id: form.device === NEW_DEVICE || !form.device ? null : form.device,
      auth_method: form.auth,
      failed_login_attempts: form.failures,
      ip_country: form.country || sender?.home_country || "DE",
      channel: "mobile_app",
    };
    simulate.mutate(body, {
      onSuccess: (detail) => {
        setResult(detail);
        setFailedAttempt(false);
        setRequestId(newRequestId()); // the next submission is a new request
      },
      onError: (error) => {
        setFailedAttempt(true);
        if (error instanceof ApiError && error.status === 409) setRequestId(newRequestId());
        if (error instanceof ApiError && error.fields.length) {
          setErrors({ form: error.fields.map((f) => `${humanize(f.field || "request")}: ${f.message}`).join(" ") });
        }
      },
    });
  };

  return (
    <>
      <PageHeader title="Payment Simulator" subtitle="Compose a payment request and see the real assessment. Results are simulated and recorded in server memory; no money moves." />
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader title="Request" subtitle="Presets fill the form from the sender's observed history. The decision always comes from the server." />
          <div className="flex flex-wrap gap-2 px-5 pb-4">
            {presets.map((p) => (
              <button key={p.id} type="button" disabled={!sender || p.disabled}
                onClick={() => change(p.apply())}
                className="min-h-11 rounded-[10px] bg-surface-2 px-3 py-1.5 text-left hover:bg-surface-3 disabled:cursor-not-allowed disabled:opacity-50">
                <span className="block text-[14px] font-semibold">{p.label}</span>
                <span className="block text-[12px] text-label-2">{p.hint}</span>
              </button>
            ))}
          </div>
          <form onSubmit={submit} noValidate className="space-y-5 border-t border-separator p-5">
            <Field label="Sender" htmlFor="sim-sender" error={errors.sender}>
              <PartyPicker id="sim-sender" accountsOnly value={form.sender} invalid={!!errors.sender} placeholder="Search accounts by name"
                onChange={(sender) => change({ sender, device: "", country: "", recipient: null })} />
            </Field>
            <div>
              <div className="mb-2 flex items-center justify-between gap-3">
                <span className="text-[13px] font-medium text-label-2">Recipient</span>
                <Segmented label="Recipient type" size="sm" value={form.recipientMode} onChange={(recipientMode) => change({ recipientMode })}
                  options={[{ value: "existing", label: "Existing" }, { value: "new", label: "New recipient" }]} />
              </div>
              {form.recipientMode === "existing" ? (
                <Field label="Existing recipient" htmlFor="sim-recipient" error={errors.recipient}>
                  <PartyPicker id="sim-recipient" value={form.recipient} invalid={!!errors.recipient} placeholder="Search accounts and payees"
                    onChange={(recipient) => change({ recipient })} />
                  {sender?.recent_recipients.length ? (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {sender.recent_recipients.slice(0, 5).map((r) => (
                        <button key={r.id} type="button" onClick={() => change({ recipient: { ...r, detail: "" } })}
                          className={cx("rounded-full px-2.5 py-1 text-[12px] font-medium", form.recipient?.id === r.id ? "bg-accent-strong text-white" : "bg-surface-2 text-label hover:bg-surface-3")}>
                          {r.name}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </Field>
              ) : (
                <Field label="New recipient name" htmlFor="sim-new" error={errors.recipient} hint="Creates a payee nobody has paid before.">
                  <input id="sim-new" className={inputClass} value={form.newName} maxLength={80} aria-invalid={!!errors.recipient || undefined}
                    onChange={(e) => change({ newName: e.target.value })} placeholder="Full name or business" />
                </Field>
              )}
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Amount (EUR)" htmlFor="sim-amount" error={errors.amount} hint={sender?.median_amount ? `Sender's recent median ${formatMoney(sender.median_amount)}` : undefined}>
                <input id="sim-amount" className={cx(inputClass, "tabular")} inputMode="decimal" type="number" min="0.01" step="0.01"
                  value={form.amount} aria-invalid={!!errors.amount || undefined} onChange={(e) => change({ amount: e.target.value })} placeholder="0.00" />
              </Field>
              <Field label="Device" htmlFor="sim-device">
                <select id="sim-device" className={inputClass} value={form.device} onChange={(e) => change({ device: e.target.value })}>
                  {(sender?.known_devices ?? []).map((d) => <option key={d} value={d}>{d} (known)</option>)}
                  <option value={NEW_DEVICE}>New device</option>
                </select>
              </Field>
              <Field label="Sign-in method" htmlFor="sim-auth">
                <select id="sim-auth" className={inputClass} value={form.auth} onChange={(e) => change({ auth: e.target.value as AuthMethod })}>
                  <option value="biometric">Biometric</option>
                  <option value="password_otp">Password and one-time code</option>
                  <option value="otp">One-time code</option>
                  <option value="password">Password only</option>
                </select>
              </Field>
              <Field label="Session country" htmlFor="sim-country">
                <select id="sim-country" className={inputClass} value={form.country} onChange={(e) => change({ country: e.target.value })}>
                  {(options.data?.countries ?? [form.country || "DE"]).map((c) => <option key={c} value={c}>{c}{c === sender?.home_country ? " (home)" : ""}</option>)}
                </select>
              </Field>
              <Field label="Failed sign-in attempts before success" htmlFor="sim-failures">
                <div className="flex items-center gap-2">
                  <Button aria-label="Fewer failed attempts" onClick={() => change({ failures: Math.max(0, form.failures - 1) })} disabled={form.failures === 0}>−</Button>
                  <output id="sim-failures" className="tabular w-8 text-center text-[17px] font-semibold">{form.failures}</output>
                  <Button aria-label="More failed attempts" onClick={() => change({ failures: Math.min(10, form.failures + 1) })} disabled={form.failures === 10}>+</Button>
                </div>
              </Field>
            </div>
            {errors.form ? <p role="alert" className="text-[13px] text-block">{errors.form}</p> : null}
            {simulate.error && !errors.form ? (
              <div role="alert" className="flex flex-wrap items-center gap-3 rounded-[10px] bg-block-soft p-3 text-[14px]">
                <span className="flex-1 text-block">{errorMessage(simulate.error)}</span>
                {failedAttempt ? <Button type="submit"><RotateCw aria-hidden className="size-4" /> Retry same request</Button> : null}
              </div>
            ) : null}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="font-mono text-[12px] text-label-2">Request ID {requestId}</p>
              <Button type="submit" variant="primary" disabled={simulate.isPending} className="min-w-44">
                {simulate.isPending ? "Assessing…" : "Submit for assessment"}
              </Button>
            </div>
          </form>
        </Card>
        <div aria-live="polite">
          {result ? <ResultCard result={result} /> : (
            <Card className="p-6">
              <h2 className="text-[17px] font-semibold">Assessment</h2>
              <p className="mt-2 text-[14px] text-label-2">
                Submit a request to see its anomaly-risk index, the four model and rule components, the corroborating signals,
                and whether the action came from the risk policy or from confirmed security evidence.
              </p>
              {options.data ? <p className="mt-4 text-[12px] text-label-2">Simulation time {formatDateTime(options.data.simulation_time)}</p> : null}
            </Card>
          )}
        </div>
      </div>
    </>
  );
}

function ResultCard({ result }: { result: AssessmentDetail }) {
  return (
    <Card className="overflow-hidden">
      <div className="space-y-2 p-5">
        <div className="flex flex-wrap items-center gap-2">
          <DecisionBadge label={result.decision_label} />
          <Chip>{SOURCE_TEXT[result.decision_source]}</Chip>
          {result.idempotent_replay ? <Chip tone="accent">Same request already recorded</Chip> : null}
        </div>
        <p className="text-[15px] font-medium">{result.explanation}</p>
        <p className="text-[13px] text-label-2">
          {result.sender.name} → {result.recipient.name} · {formatMoney(result.amount)} · {result.request_id}
        </p>
      </div>
      <div className="border-t border-separator p-5">
        <RiskComposition details={result.component_details} total={result.risk_score} verify={result.thresholds.verify} block={result.thresholds.block} />
      </div>
      {result.reasons.length ? (
        <div className="border-t border-separator px-5 py-4">
          <p className="mb-2 text-[13px] font-medium text-label-2">Triggered rules</p>
          <div className="flex flex-wrap gap-1.5">{result.reasons.map((r) => <Chip key={r.code} tone={r.corroborating ? "accent" : "neutral"}>{r.code}</Chip>)}</div>
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2 border-t border-separator p-5">
        <Link to={`/investigations/${encodeURIComponent(result.request_id)}`} className="inline-flex min-h-9 items-center gap-1 rounded-[10px] bg-accent-strong px-3.5 font-medium text-white hover:brightness-110">
          Open investigation <ArrowRight aria-hidden className="size-4" />
        </Link>
        <Link to="/live" className="inline-flex min-h-9 items-center rounded-[10px] px-3.5 font-medium text-accent hover:bg-accent-soft">See it in Live Transfers</Link>
      </div>
      <p className="border-t border-separator px-5 py-3 text-[12px] text-label-2">Simulated assessment recorded in server memory. No funds moved.</p>
    </Card>
  );
}
