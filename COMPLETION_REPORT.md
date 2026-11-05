# SecFlow completion report

Date: 5 November 2026. This is a fresh build: the working directory was empty, and no earlier
repository, dataset, or API was recovered.

## What works

- **Datasets.** Seeded generators for a 100,000-request corpus (seed 42) and an independent
  10,000-request demo history (seed 43), with 400 uniquely named accounts. Both have exact
  scenario, partition, unusual-legitimate, and cold-start counts. Labels, splits, and generator
  parameters are in separate offline files, and manifests record SHA-256 hashes. Regenerating
  reproduces byte-identical files (verified).
- **Features.** One chronological feature function serves offline replay and live scoring, with
  deterministic ordering for equal timestamps, trailing-24-hour DBSCAN profiles, and an explicit
  cold-start policy.
- **Models.** scikit-learn `IsolationForest`, `LocalOutlierFactor(novelty=True)`, and `DBSCAN` are
  fitted on days 1–60 only. Calibration-period CDF mappings put IF/LOF on `[0,1]`. A frozen-core
  DBSCAN context adapter scores new profiles, and an empty core set fails training. A bounded,
  recorded parameter search ran on validation.
- **Policy.** Weights 0.35/0.25/0.10/0.30 are preserved. The evidence-first action table is
  implemented, preventive blocks need two distinct corroborating families, and validated
  thresholds are frozen (Verify 61, Block 97). Evidence is time-aware and must come from a trusted
  source; client flags are rejected.
- **API.** All planned FastAPI routes: an idempotent simulation endpoint, serialised reviews that
  preserve the original assessment, health that reports local files and process memory, and a
  backend-owned stream that starts with the server and supports Stop, Start, and batch modes.
- **Interface.** React 19, TypeScript, Vite 8, and Tailwind 4. Overview, Live Transfers,
  Transactions, Accounts and account detail, Investigation with review, Payment Simulator (presets
  are input generators only), and Algorithm Results with the evaluation report.
- **Documentation.** README, `docs/ARCHITECTURE.md`, `docs/ALGORITHMS.md`, `docs/DATASET.md`,
  `docs/DESIGN.md`.

## Checks actually run (final state)

| Check | Result |
|---|---|
| `uv run pytest` | 89 passed |
| `uv run ruff check .` | All checks passed |
| `npm --prefix frontend test` | 14 passed (3 files) |
| `npm --prefix frontend run typecheck` | Passed (TypeScript 7.0.2) |
| `npm --prefix frontend run build` | Built: 391 kB JS, 119 kB gzipped |
| `uv run python -m backend.cli validate` | Both datasets valid; 0 cross-dataset fingerprint overlaps |

Browser verification in the built-in browser, against both dev servers:

- **Stream ownership.** The server-started stream was producing before any page opened. With two
  tabs open the rate stayed at one request per 2 seconds (5 per 10 s).
- **Stop and batch mode.** Stop halted submissions (0 in the next 7 s). Batch mode produced 5 per
  4 s.
- **Simulator → live feed → investigation → review.** The high-risk preset returned
  *Needs verification* at risk 95.1 (two corroborating families, below Block 97). The request
  appeared in Live Transfers, the investigation showed every component, and the review refused an
  empty reason. Approval was recorded as REV-00001 with the original decision Verify at 95.1
  preserved.
- **All four outcomes seen live.** Confirmed fraud evidence at risk 57.3, preventive risk block at
  98.0, Needs verification, and Permitted.
- **Mobile at 375 px.** Navigation sheet, two-line rows, collapsible filters, no horizontal
  overflow.
- **Backend restart.** The 10,000 baseline requests remained; 147 simulations and 1 review were
  discarded, the old investigation returned 404, and the stream restarted automatically.
- **Failure handling.** Stop during feed failures and same-ID retry are covered by automated
  frontend and API tests rather than a forced in-browser outage.

## Measured evaluation (final test period, synthetic)

Verify or Block caught 70.5% of fraud with 12.1% precision. Blocks caught 11.5% of fraud with
100% precision (23 blocks, 95% CI 85.7–100%). No legitimate request was blocked, and the Verify
rate was 5.74%. Model and rules alone caught 65.5% (Verify or Block). Single-request latency was
p95 4.2 ms. Full tables are in `artifacts/evaluation.md` and `docs/ALGORITHMS.md`.

## Not met or limited

- **Verify-rate goal (≤ 5%).** Not met on test (5.74%), although it was met on validation (4.94%).
- **Block-precision goal (≥ 99%).** Cannot be established from 23 blocks.
- **Preventive blocking.** Rare at the validated point. No lower block threshold avoided false
  blocks on validation, so high-risk ambiguous cases go to Verify.
- **LOF.** Adds little signal on this data (test AP 0.012).
- **Demo-history Verify share (~10%).** Higher than the test period because the demo history is
  10× sparser.
- **State.** Process memory only: it resets on restart and is not shared across workers or
  instances.
- **Scope.** No authentication or roles. No deployment, push, or cloud change was made.
