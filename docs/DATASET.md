# Datasets and provenance

Both datasets are **fully synthetic**, produced by `storage/generator.py`
(`secflow-generator-1.0.0`, schema 1.0). No real person, business, payment, or fraud case is
represented. Reproducing the requested counts does not reproduce any earlier, lost dataset byte for
byte.

## Two datasets

| | Training and evaluation corpus | Demonstration history |
|---|---|---|
| Path | `storage/data/training/` | `storage/data/demo/` |
| Seed | 42 | 43 |
| Period | 6 Apr – 14 Jul 2026 (100 days, 1,000 requests per day) | 20 Jul – 27 Oct 2026 (100 days, 100 requests per day) |
| Requests | 100,000 | 10,000 |
| Fraud / legitimate | 1,000 / 99,000 | 100 / 9,900 |
| Unusual legitimate | 5,000 | 500 |
| Per fraud scenario | 200 | 20 |
| Used for | Fitting, calibration, selection, evaluation | Product history, simulator and live-stream context only |

Both datasets share the same 400 accounts, with identical IDs, names, and creation times; the
identity seed is fixed at 42. Their requests are independent: the demo starts after the corpus ends,
and `validate` confirms zero duplicate request fingerprints across the two. The demo is never used
to select parameters or report performance.

## Partitions (corpus)

| Partition | Days | Requests | Fraud | Unusual legitimate |
|---|---|---:|---:|---:|
| train | 1–60 | 60,000 | 600 (120 per scenario) | 3,000 |
| calibration | 61–70 | 10,000 | 100 (20 per scenario) | 500 |
| validation | 71–80 | 10,000 | 100 (20 per scenario) | 500 |
| test | 81–100 | 20,000 | 200 (40 per scenario) | 1,000 |

Partitions are whole days, and every campaign stays inside one day, so it stays inside one
partition (tested).

Forty personal accounts are created during the test period and have no earlier activity. They form
the cold-start subset. Other test accounts have legitimate earlier history, so this is an
existing-customer temporal test, not an account-disjoint benchmark.

## Behaviour

**Routine payments.** Each account has generator-only behaviour: an activity rate, a typical amount,
weighted favourite payees (including shared billers and friends' accounts), one or two devices, a
sign-in mix, active hours, and a payday. Routine traffic also includes legitimate first payments to
brand-new payees, occasional failed sign-ins, foreign sessions, and permanent device replacements.
Monthly salary credits and business client payments arrive as incoming credit events.

**Unusual but legitimate (5,000).** Large planned purchases with strong sign-in, legitimate new
devices (some after failed sign-ins), travel, payroll bursts (new hires stay on the payroll),
repeated household payments, business settlements, new recipients, group payments where several
accounts pay one new payee, and account recovery after several failed sign-ins.

**Fraud (5 × 200):**

- `account_takeover`: new device, sign-in failures, foreign sessions, abrupt amounts. 20% are subtle
  (known device, no failures, ordinary amounts).
- `mule_flow`: several incoming credits, then rapid redistribution to one or two new beneficiaries.
- `velocity`: bursts of fragmented payments; 20% are slower and smaller.
- `social_engineering`: customer-authenticated payments from known devices. 40% use ordinary amounts,
  and half of those go to an established counterparty.
- `coordinated`: several accounts paying one new beneficiary within hours; 25% are spread out with
  varied amounts.

No single field identifies fraud. Fraud uses every authentication method that legitimate traffic
uses, over 1,000 legitimate requests follow failed sign-ins, legitimate traffic also pays brand-new
payees, and 240 fraud requests are labelled `is_anomaly = false` (more than 50 is asserted in the tests).

## Files

| File | Role | Contents |
|---|---|---|
| `accounts.jsonl` | runtime | ID, display name, type, home country, created at |
| `counterparties.jsonl` | runtime | External participants with understandable names |
| `requests.jsonl` | runtime | Request ID, time, sender/recipient, amount (EUR), channel, device, session, sign-in method, session country |
| `payment_events.jsonl` | runtime | Historical ledger: `transfer_settled` per request plus `incoming_credit` events |
| `authentication_events.jsonl` | runtime | `login_failure`, `login_success`, and administrative `session_revoked` events |
| `security_events.jsonl` | runtime (trusted server-side source) | Simulated evidence with recorded/effective times, expiry, status history |
| `evaluation_labels.jsonl` | **offline only** | `is_fraud`, `is_anomaly`, `scenario`, `campaign_id` |
| `split_assignments.jsonl` | **offline only** (corpus) | Partition per request |
| `generator_account_params.jsonl` | **offline only** | Generator behaviour parameters; never read by features or the service |
| `manifest.json` | metadata | Seeds, versions, date range, exact counts, cold-start IDs, evidence summary, SHA-256 per file |

The runtime loader (`load_dataset`) reads only runtime files. Labels and splits have separate
loaders that only training and evaluation call.

## Simulated security evidence

Evidence models a trusted server-side security source. It covers sessions confirmed compromised,
devices confirmed in a malware investigation, and beneficiaries confirmed to be controlled by a
fraudulent operation.

It is attached to a documented subset of campaigns:

| Fraud type | Evidence | Share of campaigns | When recorded |
|---|---|---:|---|
| Account takeover | Session | 35% | After the first payment |
| Mule flow | Beneficiary | 30% | Mid-campaign |
| Velocity, new device | Device | 25% | Before the second payment |
| Social engineering, new payee | Beneficiary | 15% | Before the campaign |
| Coordinated | Beneficiary | 40% | Before or during the campaign |

Most fraud therefore has no evidence. In the test period 20 of 200 fraud requests were covered.

Each dataset also includes ten fixtures that must never block: two each of expired, retracted,
future-recorded, pending-review, and untrusted-source evidence. All of them point at popular billers
that legitimate customers keep paying. The dataset also has 25 administrative session revocations,
which are not evidence of fraud.

All evidence is simulated. It does not constitute a real watchlist.

## Validation commands

```bash
uv run python -m backend.cli validate
```

```bash
uv run pytest backend/tests/test_dataset.py
```
