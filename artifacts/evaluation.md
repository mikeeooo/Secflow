# SecFlow evaluation report

Generated 2026-11-05T13:39:50Z · model `secflow-sk-1.0-71ecbbce2d` · policy `secflow-evidence-first-1.0.0+21de4ca9`

> Synthetic final-test period (days 81-100) of the 100,000-request training corpus. Results describe this generated data only; they are not evidence of real-world detection or fraud reduction.

Operating point (selected on validation, frozen before test): **Verify ≥ 61**, **Block ≥ 97** with at least two corroborating behaviour families (`validated`).

## Splits

| Partition | Requests | Fraud | Fraud share |
|---|---:|---:|---:|
| train | 60,000 | 600 | 1.00% |
| calibration | 10,000 | 100 | 1.00% |
| validation | 10,000 | 100 | 1.00% |
| test | 20,000 | 200 | 1.00% |

## Combined policy on the final test period

Positive definitions: *Verify or Block* — A request counts as flagged when the final action is Verify or Block. *Block only* — A request counts as flagged only when the final action is Block.

| View | Precision | Recall | F1 | FPR | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| With evidence · Verify or Block | 12.1% | 70.5% | 0.206 | 5.20% | 141 | 1029 | 59 | 18771 |
| With evidence · Block only | 100.0% | 11.5% | 0.206 | 0.00% | 23 | 0 | 177 | 19800 |
| Model + rules only · Verify or Block | 11.3% | 65.5% | 0.193 | 5.20% | 131 | 1029 | 69 | 18771 |
| Model + rules only · Block only | 100.0% | 1.5% | 0.030 | 0.00% | 3 | 0 | 197 | 19800 |

Verify rate 5.73% · Block rate 0.11% · legitimate false-block rate 0.000% · block precision 95% CI [0.8569, 1.0] over 23 blocks.

## Components alone

Flag thresholds come from the validation period (top 5% review budget; DBSCAN flags `outside_context`).

| Component | Threshold | Precision | Recall | FPR | Average precision | ROC AUC |
|---|---:|---:|---:|---:|---:|---:|
| isolation_forest | 0.954 | 10.7% | 66.0% | 5.56% | 0.243 | 0.927 |
| lof | 0.949 | 1.5% | 15.0% | 10.21% | 0.012 | 0.558 |
| dbscan | 1.000 | 6.9% | 46.5% | 6.31% | 0.038 | 0.701 |
| rules | 0.150 | 13.5% | 74.5% | 4.81% | 0.496 | 0.967 |
| combined risk score | — | — | — | — | 0.343 | 0.892 |

## Per scenario (final test)

| Scenario | Kind | Requests | Verify or Block | Block | Evidence block | Model-only Verify or Block |
|---|---|---:|---:|---:|---:|---:|
| account_recovery | legitimate | 37 | 51.4% | 0.0% | 0.0% | 51.4% |
| account_takeover | fraud | 40 | 75.0% | 2.5% | 0.0% | 75.0% |
| business_settlement | legitimate | 44 | 13.6% | 0.0% | 0.0% | 13.6% |
| coordinated | fraud | 40 | 92.5% | 12.5% | 7.5% | 92.5% |
| household_repeat | legitimate | 188 | 1.1% | 0.0% | 0.0% | 1.1% |
| large_planned_purchase | legitimate | 51 | 56.9% | 0.0% | 0.0% | 56.9% |
| mule_flow | fraud | 40 | 85.0% | 22.5% | 22.5% | 77.5% |
| new_device_legitimate | legitimate | 79 | 34.2% | 0.0% | 0.0% | 34.2% |
| new_recipient_legitimate | legitimate | 55 | 7.3% | 0.0% | 0.0% | 7.3% |
| payroll_burst | legitimate | 281 | 19.6% | 0.0% | 0.0% | 19.6% |
| routine_payment | legitimate | 18,800 | 4.2% | 0.0% | 0.0% | 4.2% |
| shared_group_payment | legitimate | 134 | 38.1% | 0.0% | 0.0% | 38.1% |
| social_engineering | fraud | 40 | 35.0% | 20.0% | 20.0% | 17.5% |
| travel | legitimate | 131 | 28.2% | 0.0% | 0.0% | 28.2% |
| velocity | fraud | 40 | 65.0% | 0.0% | 0.0% | 65.0% |

## Evidence channel versus model-only detection

- Confirmed-evidence blocks: 20 (20 fraud, 0 legitimate).
- Fraud requests without any active evidence: 180; model + rules flagged 67.2% of them (Verify or Block).
- All security evidence is simulated. The evidence channel is reported separately so it cannot hide weak model-only detection.

## Subsets

| Subset | Requests | Fraud | Verify or Block recall | Block recall | Legit review rate | Legit false-block rate |
|---|---:|---:|---:|---:|---:|---:|
| Unusual legitimate | 1,000 | 0 | n/a | n/a | 23.00% | 0.000% |
| Routine legitimate | 18,800 | 0 | n/a | n/a | 4.25% | 0.000% |
| Cold-start accounts (40) | 1,545 | 15 | 93.3% | 13.3% | 20.59% | 0.000% |
| Existing accounts | 18,455 | 185 | 68.6% | 11.4% | 3.91% | 0.000% |

## Validation goals (targets to assess, not promises)

- Legitimate false-block rate <= 0.1%: measured 0.0000 — **met**
- Verify rate <= 5%: measured 0.0573 — **not met**
- Block precision >= 99%: measured 1.0000 — **not established** (Fewer than 100 predicted blocks: the sample cannot establish 99% precision either way.)

## Latency

300 single-request assessments (single-request path: features + IF + LOF + DBSCAN context + rules + evidence + policy, in-process): mean 3.525 ms, p50 3.5 ms, p95 4.23 ms, p99 4.586 ms.

## Decision sources

- Block/confirmed_fraud_evidence: 20
- Block/risk_policy: 3
- Permit/risk_policy: 18,830
- Verify/assessment_safeguard: 11
- Verify/risk_policy: 1,136

Scores are anomaly-risk indices, not probabilities of fraud. A high score alone is never treated as confirmed fraud.
