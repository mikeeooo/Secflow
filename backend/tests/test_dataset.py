from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from storage.dataset import (
    cross_dataset_fingerprint_overlap,
    load_dataset,
    load_labels,
    load_splits,
    read_jsonl,
    validate_dataset,
)
from storage.evidence import EvidenceStore, evidence_from_row
from storage.generator import DEMO_SPEC, FRAUD_CATEGORIES, TRAINING_SPEC, generate_dataset
from storage.records import parse_ts


def test_training_corpus_has_exact_counts(generated: dict[str, Path]) -> None:
    manifest = json.loads((generated["training"] / "manifest.json").read_text())
    counts = manifest["counts"]
    assert counts["requests"] == 100_000
    assert counts["accounts"] == 400
    assert counts["fraud"] == 1_000
    assert counts["legitimate"] == 99_000
    assert counts["unusual_legitimate"] == 5_000
    assert counts["routine_legitimate"] == 94_000
    for category in FRAUD_CATEGORIES:
        assert counts["by_scenario"][category] == 200
    expected = {
        "train": (60_000, 600, 3_000),
        "calibration": (10_000, 100, 500),
        "validation": (10_000, 100, 500),
        "test": (20_000, 200, 1_000),
    }
    for name, (requests, fraud, unusual) in expected.items():
        bucket = counts["by_partition"][name]
        assert (bucket["requests"], bucket["fraud"], bucket["unusual_legitimate"]) == (requests, fraud, unusual)
        assert set(bucket["fraud_by_category"].values()) == {fraud // 5}


def test_demo_dataset_has_exact_counts(generated: dict[str, Path]) -> None:
    counts = json.loads((generated["demo"] / "manifest.json").read_text())["counts"]
    assert (counts["requests"], counts["accounts"], counts["fraud"], counts["legitimate"]) == (10_000, 400, 100, 9_900)
    assert counts["unusual_legitimate"] == 500
    for category in FRAUD_CATEGORIES:
        assert counts["by_scenario"][category] == 20


def test_validation_passes_for_both_datasets(generated: dict[str, Path]) -> None:
    assert validate_dataset(generated["training"], TRAINING_SPEC) == []
    assert validate_dataset(generated["demo"], DEMO_SPEC) == []


def test_same_seed_reproduces_identical_files(generated: dict[str, Path], tmp_path: Path) -> None:
    again = generate_dataset(tmp_path / "demo", DEMO_SPEC)
    original = json.loads((generated["demo"] / "manifest.json").read_text())
    assert {k: v["sha256"] for k, v in again["files"].items()} == {
        k: v["sha256"] for k, v in original["files"].items()
    }


def test_accounts_are_stable_and_uniquely_named_across_datasets(generated: dict[str, Path]) -> None:
    training = read_jsonl(generated["training"] / "accounts.jsonl")
    demo = read_jsonl(generated["demo"] / "accounts.jsonl")
    assert training == demo
    names = [a["display_name"] for a in training]
    assert len(set(names)) == 400
    assert all(" " in name for name in names)


def test_runtime_files_never_contain_labels(generated: dict[str, Path]) -> None:
    forbidden = {"is_fraud", "is_anomaly", "scenario", "campaign_id", "partition", "expected_decision"}
    for name in ("requests.jsonl", "payment_events.jsonl", "authentication_events.jsonl", "accounts.jsonl"):
        first = read_jsonl(generated["training"] / name)[0]
        assert not forbidden & set(first), name
    dataset = load_dataset(generated["demo"])
    assert not hasattr(dataset.requests[0], "is_fraud")


def test_demo_is_independent_and_after_corpus(generated: dict[str, Path]) -> None:
    assert cross_dataset_fingerprint_overlap(generated["training"], generated["demo"]) == 0
    training_last = read_jsonl(generated["training"] / "requests.jsonl")[-1]["timestamp"]
    demo_first = read_jsonl(generated["demo"] / "requests.jsonl")[0]["timestamp"]
    assert parse_ts(demo_first) > parse_ts(training_last)


def test_campaigns_stay_in_one_partition(generated: dict[str, Path]) -> None:
    labels = load_labels(generated["training"])
    splits = load_splits(generated["training"])
    parts: dict[str, set[str]] = {}
    for request_id, label in labels.items():
        if label["campaign_id"]:
            parts.setdefault(label["campaign_id"], set()).add(splits[request_id])
    assert parts and all(len(p) == 1 for p in parts.values())


def test_forty_cold_start_accounts_first_request_in_test(generated: dict[str, Path]) -> None:
    manifest = json.loads((generated["training"] / "manifest.json").read_text())
    cold = set(manifest["cold_start"]["account_ids"])
    assert len(cold) == 40
    splits = load_splits(generated["training"])
    first_partition: dict[str, str] = {}
    for row in read_jsonl(generated["training"] / "requests.jsonl"):
        first_partition.setdefault(row["sender_id"], splits[row["request_id"]])
    assert all(first_partition.get(a) == "test" for a in cold)
    assert sum(1 for a, p in first_partition.items() if p == "test") == 40


def test_fraud_is_not_identified_by_one_field(generated: dict[str, Path]) -> None:
    labels = load_labels(generated["training"])
    dataset = load_dataset(generated["training"])
    fraud_methods = Counter(r.auth_method for r in dataset.requests if labels[r.request_id]["is_fraud"])
    legit_methods = Counter(r.auth_method for r in dataset.requests if not labels[r.request_id]["is_fraud"])
    assert set(fraud_methods) <= set(legit_methods)
    subtle_fraud = sum(1 for l in labels.values() if l["is_fraud"] and not l["is_anomaly"])
    assert subtle_fraud > 50
    failures = {e.session_id for e in dataset.auth_events if e.event_type == "login_failure"}
    legit_with_failures = sum(
        1 for r in dataset.requests if r.session_id in failures and not labels[r.request_id]["is_fraud"]
    )
    assert legit_with_failures > 1_000


def test_security_evidence_is_time_aware(generated: dict[str, Path]) -> None:
    rows = read_jsonl(generated["training"] / "security_events.jsonl")
    store = EvidenceStore(
        [evidence_from_row(r) for r in rows],
        trusted_sources=("bank_security_operations", "fraud_investigations_unit"),
        blocking_types=("compromised_session", "fraud_controlled_beneficiary", "compromised_device"),
    )
    fixtures = [evidence_from_row(r) for r in rows if r["note"].startswith("Fixture")]
    assert len(fixtures) == 10
    dataset = load_dataset(generated["training"])
    fixture_entities = {f.entity_id for f in fixtures}
    paid_to_fixtures = [r for r in dataset.requests if r.recipient_id in fixture_entities]
    assert paid_to_fixtures, "fixtures must reference entities that legitimate requests use"
    assert all(not store.active_for(r) for r in paid_to_fixtures)
    campaign = [evidence_from_row(r) for r in rows if not r["note"].startswith("Fixture")]
    assert all(e.recorded_at >= e.effective_from or e.entity_type != "counterparty" for e in campaign)
