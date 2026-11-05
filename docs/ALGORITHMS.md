# Algorithms, policy, and measured results

All three estimators are imported from scikit-learn 1.9.1. Nothing is re-implemented.

## Features

`ml/features.py` (`features-1.0.0`) builds two vectors per request, using only events before the
request.

**Payment vector (20 values):** log amount; amount z-score against the sender's 30-day amounts;
log ratio to the 30-day maximum; requests in the last hour and the last 24 hours; log 24-hour sum;
24-hour pace relative to the usual daily rate (normalised by account age when younger than 30
days); unique recipients in 24 hours; no established beneficiary relationship (never paid, or first
paid under 24 hours ago); other senders paying the beneficiary in 24 hours; log beneficiary age;
log device age; failed sign-ins in 24 hours; log hours since the previous request; log account age;
log incoming funds in 24 hours; foreign session; weak authentication; hour-of-day deviation; log
requests in 30 days.

**Account-context vector (8 values, for DBSCAN):** the trailing-24-hour prospective profile. It
covers request count, sum, unique and new recipients, devices, failed sign-ins, incoming funds, and
the 24-hour sum relative to the usual daily sum.

IDs, names, labels, scenarios, campaign IDs, split assignments, and generator parameters are never
numeric inputs.

## Fitting and score mapping

| Step | Data | Labels used? |
|---|---|---|
| Winsorise (0.5/99.5%) and `StandardScaler` | train, days 1–60 (60,000) | No |
| `IsolationForest`, `LocalOutlierFactor(novelty=True)` | train (60,000) | No |
| `DBSCAN` on scaled 24 h profiles | seeded 20,000-profile subsample of train profiles with ≥ 3 prior requests | No |
| IF/LOF empirical CDF mappings | calibration, days 61–70 (10,000) | No |
| Parameter choice, Verify/Block thresholds | validation, days 71–80 (10,000) | Yes |
| Final report | test, days 81–100 (20,000) | Yes, once, after freezing |

The DBSCAN subsample bounds neighbourhood memory and is drawn without looking at labels.

**Score direction.** IF uses `-score_samples` and LOF uses `-score_samples` on unseen rows; in both,
a higher value means more anomalous. Each is mapped through the calibration-period empirical CDF
(`searchsorted(side="right") / n`), giving a value in `[0, 1]`. Below the reference minimum maps to
0, at or above the maximum maps to 1, and ties resolve deterministically.

**LOF novelty.** The novelty methods are never applied to fitting rows. Training diagnostics read
`negative_outlier_factor_`.

**DBSCAN context adapter (application heuristic).** DBSCAN cannot predict online, so SecFlow freezes
the training core samples (18,014 cores, 122 clusters, 6.7% training noise at `eps = 0.891`,
`min_samples = 5`) and scores each new profile:

- within `eps` of any core sample → 0 (`within_context`);
- beyond every core neighbourhood → 1 (`outside_context`);
- fewer than three earlier requests → 0 (`insufficient_history`).

An empty core set raises `EmptyCoreError` during training. This is context, not a fraud verdict.

### Bounded search (selected on validation)

| Estimator | Candidates | Selected |
|---|---|---|
| IsolationForest | `n_estimators` 100/200 × `max_samples` 256/512, seed 42 | 100 trees, 512 samples |
| LOF | `n_neighbors` 20/35/50 | 50 |
| DBSCAN | `min_samples` 5/10/20 × `eps` at the 90/95/98th percentile of training k-distances | 5, `eps` 0.891 |

Every candidate's validation score is stored in `ml/models/training_report.json` and shown on the
Algorithm Results page.

## Rules

Rules are defined in `config/policy.json` with stable codes, weights, and families. The rules score
is `min(1, Σ weights of triggered rules)`.

| Code | Family | Weight | Corroborates |
|---|---|---:|:-:|
| `AMOUNT_SPIKE` | amount deviation | 0.30 | ✓ |
| `AMOUNT_ELEVATED` | amount deviation | 0.10 | |
| `NEW_BENEFICIARY_HIGH_AMOUNT` | amount deviation | 0.20 | ✓ |
| `VELOCITY_BURST` | velocity | 0.30 | ✓ |
| `RECIPIENT_FANOUT` | velocity | 0.10 | |
| `NEW_DEVICE_AFTER_FAILED_LOGINS` | device & sign-in | 0.35 | ✓ |
| `REPEATED_FAILED_LOGINS` | device & sign-in | 0.15 | ✓ |
| `NEW_DEVICE` | device & sign-in | 0.10 | |
| `FOREIGN_SESSION` | device & sign-in | 0.10 | |
| `SHARED_NEW_BENEFICIARY` | beneficiary network | 0.30 | ✓ |
| `NEW_BENEFICIARY` | beneficiary network | 0.05 | |
| `PASS_THROUGH_FUNDS` | pass-through funds | 0.30 | ✓ |

Corroboration counts **families**, not rules. Several rules derived from the same failed-sign-in
fact count once. IF and LOF agreeing is never counted as corroboration.

History-dependent rules (amount deviation, device change, beneficiary novelty) do not fire for an
account with no history; missing history is never turned into evidence of fraud.

## Combination and action table

`combine_scores` returns the unrounded total and per-component contributions, which sum exactly to
the total. Decisions use the unrounded value; only the interface rounds.

| Priority | Condition | Action | `decision_source` |
|---|---|---|---|
| 1 | Active trusted confirmed-fraud evidence at request time | Block (“Confirmed fraud evidence”) | `confirmed_fraud_evidence` |
| 2 | Models unavailable, invalid features, or no history with an amount above €500 or without strong sign-in | Verify | `assessment_safeguard` |
| 3 | Risk ≥ Block threshold **and** ≥ 2 distinct corroborating families | Block (“Preventive risk block”) | `risk_policy` |
| 4 | Risk ≥ Verify threshold (including very high risk without corroboration) | Verify | `risk_policy` |
| 5 | Otherwise | Permit | `risk_policy` |

Evidence is active only if it was recorded at or before the request time, is effective then (and
not expired), has `confirmed` as its latest status at that time, comes from a configured trusted
source, and has a blocking evidence type. Expired, retracted, future, pending-review, and
untrusted-source fixtures are in both datasets and never block (tested).

## Operating point and its tradeoff

The thresholds were chosen by a 51 × 54 grid search on validation, using model and rules only (no
evidence). The search maximised Verify-or-Block recall subject to three constraints: Verify rate
≤ 5%, legitimate false-block rate ≤ 0.1%, and zero false blocks among predicted blocks (the 99%
precision goal cannot be estimated from a handful of blocks, so any false block disqualifies).

| | Verify ≥ | Block ≥ | Validation recall (V or B) | Validation verify rate | Validation blocks |
|---|---:|---:|---:|---:|---:|
| Initial candidate | 35 | 70 | 94% | **42.4%** | 50 (24 false) |
| Selected (`op-7edcea41`) | **61** | **97** | 68% | 4.9% | 0 |

The 35/70 starting point is unusable with calibrated components. An ordinary request scores about
30, because each model component is a percentile against the reference period.

No preventive-block threshold below 97 avoided false blocks on validation: corroborated high-risk
legitimate behaviour (payroll bursts, group payments, new-device travel) overlaps the fraud
campaigns. Following the specification, ambiguous high-risk cases therefore stay in Verify, and
automatic blocking relies mainly on confirmed evidence.

## Final test results (days 81–100, 20,000 requests, 200 fraud)

Positive = Verify or Block, or Block only. From `artifacts/evaluation.json`.

| View | Precision | Recall | F1 | FPR |
|---|---:|---:|---:|---:|
| Full policy · Verify or Block | 12.1% | 70.5% | 0.206 | 5.20% |
| Full policy · Block only | 100% (23/23, 95% CI 85.7–100%) | 11.5% | 0.206 | 0.00% |
| Model + rules only · Verify or Block | 11.3% | 65.5% | 0.193 | 5.20% |
| Model + rules only · Block only | 100% (3/3) | 1.5% | 0.030 | 0.00% |

| Component alone (validation top-5% threshold) | Precision | Recall | Average precision | ROC AUC |
|---|---:|---:|---:|---:|
| IsolationForest | 10.7% | 66.0% | 0.243 | 0.927 |
| LOF (novelty) | 1.5% | 15.0% | 0.012 | 0.558 |
| DBSCAN context (`outside_context`) | 6.9% | 46.5% | 0.038 | 0.701 |
| Rules | 13.5% | 74.5% | 0.496 | 0.967 |
| Combined risk index | — | — | 0.343 | 0.892 |

| Fraud scenario | Verify or Block | Block | Evidence block | Model + rules only |
|---|---:|---:|---:|---:|
| account_takeover | 75.0% | 2.5% | 0.0% | 75.0% |
| coordinated | 92.5% | 12.5% | 7.5% | 92.5% |
| mule_flow | 85.0% | 22.5% | 22.5% | 77.5% |
| social_engineering | 35.0% | 20.0% | 20.0% | 17.5% |
| velocity | 65.0% | 0.0% | 0.0% | 65.0% |

Other measurements:

- **Evidence channel.** 20 confirmed-evidence blocks, all fraud and none legitimate. 180 fraud
  requests had no active evidence; model and rules flagged 67.2% of them.
- **Unusual-legitimate requests (1,000).** 23.0% reviewed, 0.0% blocked.
- **Cold-start accounts (40 accounts, 1,545 requests, 15 fraud).** Fraud recall 93.3%; 20.6% of
  their legitimate requests reviewed; 0.0% blocked.
- **Goals.** False-block rate ≤ 0.1%: met. Verify rate ≤ 5%: **not met** (5.74% on test; 4.94% on
  validation). Block precision ≥ 99%: not established (only 23 blocks).
- **Latency (300 single-request assessments, in process).** Mean 3.5 ms, p95 4.2 ms, p99 4.6 ms.

### Honest reading

- **LOF contributes little on this data.** Its novelty scores barely separate fraud (AP 0.012).
  The fixed 0.25 weight still lets it move scores; the weights are kept because the brief fixes
  them. The combined index (AP 0.343) is below the rules alone (0.496).
- **Social engineering is the hardest case:** customer-authenticated payments from known devices.
  Without evidence, model and rules catch 17.5% of it.
- **Earlier numbers are not targets.** An earlier implementation reported 75% recall and 8.82%
  precision on a different dataset. Those figures are not acceptance targets, and the numbers above
  are not comparable to them.
