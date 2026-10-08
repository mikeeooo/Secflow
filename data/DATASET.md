# SecFlow dataset

The dataset is prepared from the original PaySim CSV plus reproducible generated scenarios. All payment activity is synthetic. No connection to MIA or a bank is involved.

## Files

| File | Content |
|---|---|
| `generated/secflow_transactions.csv` | Main application input: PaySim subset and generated scenarios, sorted chronologically. |
| `generated/paysim_extended.csv` | Only the selected PaySim rows, with generated timing and security metadata. |
| `generated/generated_scenarios.csv` | Normal histories and generated demonstration scenarios. |
| `generated/accounts.csv` | Account identifiers and descriptive dataset-wide activity totals. |
| `generated/devices.csv` | Account/device relationships and first/last observation times. |
| `generated/authentication_events.csv` | Individual failed and successful login attempts linked to transactions and sessions. |
| `generated/manifest.json` | Counts, selection method, seed, provenance, exclusions, and SHA-256 checksums. |
| `raw/PS_20174392719_1491204439457_log.csv` | Complete original PaySim CSV, unchanged. |
| `raw/paysim.zip` | Original downloaded archive. |

## Current working dataset

- **54,520 transactions:** 50,000 PaySim rows and 4,520 generated rows.
- **100 source fraud labels** and **580 generated fraud labels**, reported separately.
- **11 scenario categories**, with 10 episodes per category and normal history before each episode.
- **78,969 account identifiers**, **50,220 account/device relationships**, and **60,815 authentication events**.
- PaySim selection: first 50,000 rows in original chronological order, covering source hours 1–9. No fraud oversampling or class balancing.
- Seed: `42`. The full original CSV is available locally for larger future experiments.

This prefix supports a local demonstration. It is not a representative sample of the whole month. Source accounts can have little history within the selected slice; generated episodes provide coherent histories for demonstration.

## Added fields

The original eleven PaySim fields are preserved. Added fields include `transaction_id`, `source_row_id`, `timestamp_seconds`, `device_id`, `is_new_device`, `session_id`, `login_attempts`, `failed_login_attempts`, `data_origin`, `security_metadata_origin`, `timestamp_origin`, `scenario_type`, `scenario_id`, `ground_truth_fraud`, and `currency`.

`timestamp_seconds = (step - 1) * 3600 + offset_seconds`. Offsets are generated within the original hour, preserve source row order, and can coincide. They are not recovered real timestamps. No calendar date is implied.

Device and authentication fields are generated. The first observed device is marked new even for a legitimate account. PaySim security metadata generation is independent of `isFraud`. Each session ends with a successful login after zero or more failed attempts; authentication timestamps do not occur after the associated transfer.

Amounts retain their own units: `PAYSIM_UNIT` for source transactions and `DEMO_UNIT` for generated scenarios. Neither is asserted to be MDL. Filter by origin/currency when aggregating values; do not combine them into a purported bank-wide monetary total.

## Generated scenarios

- `unusual_amount`
- `repeated_transfers`
- `amount_fragmentation`
- `account_takeover`
- `mule_account`
- `suspicious_beneficiary`
- `coordinated_activity`
- `scam_related_transfer`
- `legitimate_large_payment`
- `legitimate_new_device`
- `legitimate_burst`

`normal_history` contains the normal activity preceding these episodes. Generated accounts use a separate `SIM_` namespace. All generated transactions use `TRANSFER`. Labels describe the generator's scenario, not independent confirmation of a real fraud.

Large legitimate payments overlap deliberately with unusual fraudulent amounts. Legitimate bursts and device changes make it possible to test false positives. For mule scenarios, several funded senders transfer to the mule, which then forwards 98% of the received value. No scenario claims that a behavioral signal uniquely proves fraud.

## Detection and evaluation

Do not use fraud labels, source markers, scenario categories/identifiers, or PaySim balance columns as detection features. The complete exclusion list is in the manifest. Transaction identifiers are join keys, not numerical algorithm features. Dataset-wide account totals and device last-seen times are descriptive, retrospective exports; compute causal features from prior events instead.

Use `isFraud` for the PaySim benchmark and `ground_truth_fraud` for generated-scenario evaluation. Evaluate them separately. Source timing originally has only hourly precision, so second-level features belong to the simulated extension evaluation.

Split chronologically and fit preprocessing only on the reference/training portion. The algorithms have not yet been implemented; these CSV files contain labels and observations, not precomputed model scores or blocking decisions.

## Rebuild and verify

Run from the repository root with Python 3.10 or later. No third-party packages are required for dataset preparation.

```bash
python3 datasets/prepare_dataset.py --limit 50000 --repeats 10 --seed 42
python3 -m unittest discover -s tests -v
```

The generator reads the local original CSV. To use a different file, pass `--source /path/to/paysim.csv`. `--output` selects another output directory. The same source, seed, limits, and generator produce byte-identical outputs. Raw data and generated CSV exports are excluded from Git; the code and this guide are suitable for the repository.

## Source and attribution

[PaySim dataset](https://www.kaggle.com/datasets/ealaxi/paysim1/data), downloaded through Kaggle's public dataset endpoint. Published under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

Dataset citation: E. A. Lopez-Rojas, A. Elmir, and S. Axelsson. *PaySim: A financial mobile money simulator for fraud detection.* European Modeling and Simulation Symposium, 2016.
