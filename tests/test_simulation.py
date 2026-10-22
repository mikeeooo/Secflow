from datetime import timezone

from mia_demo.simulation.generator import generate, load_dataset


def test_generator_is_reproducible_and_labels_are_private():
    first = generate(seed=7, accounts=30, attempts=500)
    second = generate(seed=7, accounts=30, attempts=500)
    assert first.fingerprint() == second.fingerprint()
    assert len(first.requests) == 500
    assert len({r["transaction_id"] for r in first.requests}) == 500
    assert all(r["amount_bani"] > 0 and "scenario_type" not in r for r in first.requests)
    assert all(e.observed_at.tzinfo == timezone.utc for e in first.events)


def test_balances_reconcile_and_scenarios_stay_in_a_split():
    dataset = generate(seed=42, accounts=40, attempts=600)
    balances = {key: value["initial_balance_bani"] for key, value in dataset.accounts.items()}
    external_net = 0
    for event in dataset.events:
        if event.event_type == "incoming":
            balances[event.receiver_account_id] += event.amount_bani
            external_net += event.amount_bani
        elif event.event_type == "completed":
            balances[event.sender_account_id] -= event.amount_bani
            if event.receiver_psp == "LOCAL":
                balances[event.receiver_account_id] += event.amount_bani
            else:
                external_net -= event.amount_bani
        assert all(balance >= 0 for balance in balances.values())
    assert sum(balances.values()) == sum(a["initial_balance_bani"] for a in dataset.accounts.values()) + external_net
    by_scenario = {}
    for request in dataset.requests:
        label = dataset.labels.get(request["transaction_id"])
        if label:
            by_scenario.setdefault(label["scenario_id"], set()).add(request["split"])
    assert by_scenario and all(len(splits) == 1 for splits in by_scenario.values())
    assert set(label["scenario_type"] for label in dataset.labels.values()) == {"account_takeover", "mule_flow", "velocity", "social_engineering", "coordinated"}


def test_saved_dataset_keeps_labels_separate_and_loads_identically(tmp_path):
    dataset = generate(seed=3, accounts=20, attempts=200)
    manifest = dataset.save(tmp_path)
    assert manifest["fingerprint"] == dataset.fingerprint()
    assert not (tmp_path / "evaluation_labels.jsonl").exists()
    loaded = load_dataset(tmp_path)
    assert loaded.fingerprint() == dataset.fingerprint()


def test_unseen_account_population_can_be_generated():
    baseline = generate(seed=1, accounts=10, attempts=100)
    unseen = generate(seed=2, accounts=10, attempts=100, account_prefix="U")
    assert set(baseline.accounts).isdisjoint(unseen.accounts)


def test_larger_dataset_keeps_target_prevalence_and_periods():
    dataset = generate(seed=42, accounts=100, attempts=11000)
    assert len(dataset.requests) == 11000
    assert len(dataset.labels) == 110
    labelled = [row for row in dataset.requests if row["transaction_id"] in dataset.labels]
    assert {row["split"] for row in labelled} == {"train", "calibration", "validation", "test"}
