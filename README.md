# SecFlow

Local university prototype for investigating simulated instant-payment anomalies. Django + SQLite backend, server-rendered frontend, and dependency-free Isolation Forest, DBSCAN and LOF implementations. English, minimalist blue-and-white interface.

## Run locally

Python 3.11+ is recommended. From this directory:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
export SECFLOW_DEMO_PASSWORD='choose-your-local-password'
.venv/bin/python manage.py setup_demo
.venv/bin/python manage.py benchmark
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Open http://127.0.0.1:8000. Users `admin` and `analyst` receive the password you set **only when first created**. Admin manages users at `/admin/`, imports, and detection parameters. Analyst can investigate cases, simulate transfers, and change account restrictions with a reason. All changes require authentication and CSRF tokens.

The workspace already has a prepared local demo: `admin` / `analyst`, password `SecFlow-demo-2026!`. These are disposable local demonstration credentials. Bind the development server to localhost. This is not a production banking service.

## What works

- Dashboard: actual database totals, simulated activity, separate currency units, open cases, and labeled simulation impact.
- Transactions: search, source/decision filters, pagination, detailed algorithm evidence, and CSV export.
- Fraud Cases: assignment to the investigating user, notes, status, and resolution outcome.
- Accounts: incoming/outgoing history, device history, risk, and auditable restrictions. Unblocking never executes an earlier rejected transfer.
- Algorithm Results: configurable replay, raw scores, causal DBSCAN clusters/noise, separate validation/test confusion matrices and metrics for each source, rules-only and ensemble comparisons, original PaySim benchmark, timing/memory scaling, JSON export and print layouts.
- Simulation: create a new transfer between generated accounts, run detection, and inspect its decision/case. Manual transfers have unknown ground truth and are excluded from evaluation metrics.
- Django administration: user management, operational objects and stored run history.

## Data and reproducibility

`data/generated/manifest.json` records the prepared data provenance. The demo imports the first 2,000 PaySim rows plus all 4,520 generated scenario rows: 6,520 transactions. Run `setup_demo --paysim-limit 0` to import the full prepared dataset; zero means no PaySim limit. Import is idempotent and validates required fields, nonnegative finite amounts, labels, IDs and timestamps. Original CSV files remain untouched. The import checksum includes its selection policy.

Per source, the first 128 rows form a fixed reference, the next 64 are validation, and the remaining rows form the test set. All features use only earlier requests. Scaler, Isolation Forest and LOF reference density are fitted only on the reference rows. DBSCAN uses the trailing 24 observations through the current request. Its cluster identifiers are **window-local**, not persistent account groups. Reference rows stay Pending by design.

Operational risk uses fixed demonstrator thresholds, not a claim of calibrated probability. The default score is `0.30 × IF + 0.25 × LOF + 0.15 × DBSCAN noise + 0.30 × rules`, on a 0–100 scale; Review >=45 and Block >=65. A restricted sender's subsequent request is also blocked. Reruns append assessments while preserving initial decisions, cases, and analyst corrections. Raw request history includes blocked attempts, because it models attempted activity.

`benchmark` evaluates the original PaySim prefix without generated metadata or balances, using original hourly timing. Thresholds are selected on its validation split and reported on a held-out test. Small chronological prefixes may contain very few positive cases; results are demonstration evidence, not generalization claims. `artifacts/benchmark.json` contains the exact metrics and runtime/allocation measurements. Peak memory measures Python allocations via tracemalloc, not total process RSS. Scoring latency and fitted object sizes vary by hardware.

## Verification

```sh
.venv/bin/python manage.py test tests
.venv/bin/python manage.py check
```

Tests cover known clusters, duplicate/tied neighbors, random seed reproducibility, causal features, label exclusion, authentication, role boundaries, CSRF, imports, case outcomes, and durable manual corrections. Existing dataset provenance tests are preserved.

## Project map

- `BLUEPRINT.md`: original product specification.
- `core/`: database models, HTTP views, workflows, migrations, management commands.
- `detection/algorithms.py`: algorithms implemented from scratch.
- `detection/features.py`: causal features and reference-only scaling.
- `detection/evaluation.py`: confusion matrices and metrics.
- `templates/`, `static/`: responsive UI.
- `datasets/prepare_dataset.py`: reproducible source extension and scenarios.
- `docs/ALGORITHMS.md`: formulas, complexity and interpretation.

## Scope and boundaries

All transfers, blocks, devices and login events are simulated. No commercial API or bank integration is included. The runtime analysis is synchronous and bounded for a local academic demo, not a distributed stream processor. Operational thresholds remain fixed hypotheses; the original-data benchmark demonstrates validation-based selection separately. The later university report is outside this implementation stage. Large datasets require batching and a background worker before multi-user deployment.
