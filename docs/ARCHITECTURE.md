# Architecture and data flow

```text
                 offline (CLI)                                   online (one uvicorn process)
┌────────────────────────────────────────────┐      ┌──────────────────────────────────────────────────────┐
│ generate ─► storage/data/{training,demo}   │      │ startup: load demo runtime files + model bundle      │
│              (JSONL + manifest, hashes)    │      │          + policy + operating point + evidence       │
│ train    ─► replay ─► features ─► fit IF,  │      │          replay 10,000 baseline requests (batch)     │
│              LOF, DBSCAN on days 1-60      │─────►│                                                      │
│              CDF maps on days 61-70        │ ml/  │ request ─► append session events to history overlay  │
│              select params/thresholds 71-80│models│          ─► build_features (history < key)           │
│ evaluate ─► frozen pipeline on days 81-100 │      │          ─► IF, LOF, DBSCAN context (once each)      │
│              ─► artifacts/evaluation.*     │      │          ─► rules ─► combine ─► evidence ─► action   │
└────────────────────────────────────────────┘      │          ─► commit attempt (+ settlement if Permit)  │
                                                     │ stream producer (asyncio task) ─► same path         │
                                                     └───────────────▲──────────────────────────────────────┘
                                                                     │ /api (JSON)
                                                     ┌───────────────┴──────────────────────────────────────┐
                                                     │ React app: Overview, Live Transfers, Transactions,   │
                                                     │ Accounts, Investigation, Simulator, Algorithm Results│
                                                     └──────────────────────────────────────────────────────┘
```

## One assessment path

`ml/assess.py` is the only path from a request to a decision. Live simulations, the startup replay
of the demo history, and the offline evaluation all call it.

1. `build_features(request, key, history, account)` reads only events whose ordering key is lower
   than the request's key.
2. `ModelBundle.score_batch` runs the preprocessor, IsolationForest, LOF and the DBSCAN context
   adapter exactly once per row.
3. `evaluate_rules` turns observed facts into reason codes, weights, and corroboration families.
4. `combine_scores` is a pure function of the four component values.
5. `EvidenceStore.active_for` returns trusted evidence active at the request time.
6. `decide_action` applies the evidence-first action table.

## Ordering and leakage control

Every event gets an ordering key `epoch_seconds × 10^6 + sequence`. Events that share a second are
ordered authentication → payment → request, then by identifier, so equal timestamps resolve
deterministically. Queries take the target key and use `bisect_left`, so appending future events
cannot change earlier features. Tests cover this (`backend/tests/test_features.py`).

History aggregates exclude the request under assessment. The DBSCAN account-context profile is
*prospective*: the sender's trailing 24 hours of history plus the request being assessed, kept as
a separate vector.

Attempted activity (every request, whatever its decision) feeds velocity and beneficiary
features. Completed flows (settlement and incoming-credit events) feed the incoming-funds
features. A blocked or pending simulation therefore counts as an attempt but never as money
received by anyone.

## State, idempotency and concurrency

`storage/memory.py` keeps assessments, reviews, idempotency fingerprints, and the history overlay
behind one re-entrant lock.

- `POST /api/simulations` hashes the payload. The same ID with the same payload returns the stored
  assessment (`200`, `idempotent_replay: true`) and writes no duplicate events. The same ID with a
  different payload returns `409`.
- Scoring and commit happen under the lock, so concurrent duplicates commit exactly once (tested
  with eight parallel requests).
- Reviews are serialised the same way: the first final outcome wins and later attempts get `409`.
- The original automated decision and score are immutable. A review stores its own record and
  changes only the payment outcome (`approved_after_review` or `rejected_after_review`).

**Limitations:** state is lost on restart and is not shared between workers or instances. Durable,
multi-instance operation would need a shared store and is a separate scope change.

## Simulation clock

Baseline events are historical. The simulation clock starts one hour after the last demo event and
advances in real time. A simulation's sign-in events and request are stamped at or after the
latest event, so the overlay stays strictly ordered.

## Live stream

`backend/stream.py` owns one producer task per process. It starts with the server (unless
`SECFLOW_AUTOSTART_STREAM=false`) and submits one request every 2 seconds, or batches of 5, 10 or
20 every 4 seconds. Browsers poll `GET /api/live-transfers?after=<cursor>` and only call
start, stop or mode, so extra tabs cannot multiply submissions.

The producer re-checks `running` before every submission, so Stop takes effect within one
submission. Stop does not depend on the feed endpoint, so it keeps working while feed polling fails.

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | Readiness, data source, model/policy versions, memory-state disclosure |
| GET | `/api/overview` | Totals, volumes, daily trend, recent activity, review queue |
| GET | `/api/transactions` | Filter (`q`, `decision`, `decision_source`, `origin`, `review_status`, dates, score) and paginate |
| GET | `/api/accounts`, `/api/accounts/{id}` | Named-account search, behaviour profile, context finding, linked transfers |
| GET | `/api/parties` | Account and counterparty search for the simulator |
| GET | `/api/simulator/options` | Known devices, recent recipients, beneficiaries with active evidence |
| POST | `/api/simulations` | Assess and record one simulated request (idempotent) |
| GET | `/api/live-transfers` | Cursor-based simulated assessments plus stream status |
| GET/POST | `/api/simulation-stream[/start\|/stop\|/mode]` | Backend producer status and controls |
| GET | `/api/investigations/{id}` | Full assessment, timeline, reviews |
| POST | `/api/investigations/{id}/reviews` | Approve or reject a Verify request with a required reason |
| GET | `/api/algorithms`, `/api/evaluation` | Model metadata, distributions, search records, evaluation report |

Errors share one shape: `{"error": {"code", "message", "details"}}`. Unknown request fields are
rejected (`422`), so a client cannot send `is_fraud` or `confirmed_fraud` to influence a decision.
