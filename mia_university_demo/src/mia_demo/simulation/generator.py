"""Deterministic synthetic PSP-visible payment stream and private labels."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import json
import math
import random

from mia_demo.schemas import PaymentEvent


# The frozen demo ends on the project's presentation date so live scoring has
# recent history in its 30-day feature window. Keep the date fixed for replay.
START = datetime(2026, 7, 13, tzinfo=timezone.utc)
SCENARIOS = ("account_takeover", "mule_flow", "velocity", "social_engineering", "coordinated")


def load_dataset(directory: str | Path):
    directory = Path(directory)

    def read_rows(path):
        with path.open(encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    accounts = {}
    for row in read_rows(directory / "accounts.jsonl"):
        accounts[row.pop("account_id")] = row
    events = [PaymentEvent.model_validate(row) for row in read_rows(directory / "events.jsonl")]
    labels = {}
    for row in read_rows(directory / "private" / "evaluation_labels.jsonl"):
        labels[row.pop("transaction_id")] = row
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    balances = json.loads((directory / "closing_balances.json").read_text(encoding="utf-8"))
    dataset = GeneratedDataset(accounts, events, read_rows(directory / "sessions.jsonl"), read_rows(directory / "account_events.jsonl"), read_rows(directory / "requests.jsonl"), labels, balances, manifest["config"])
    if dataset.fingerprint() != manifest["fingerprint"]:
        raise ValueError("Dataset fingerprint mismatch")
    return dataset


def split_for_day(day: int) -> str:
    if day <= 10:
        return "warmup"
    if day <= 60:
        return "train"
    if day <= 70:
        return "calibration"
    if day <= 80:
        return "validation"
    return "test"


@dataclass
class GeneratedDataset:
    accounts: dict[str, dict]
    events: list[PaymentEvent]
    sessions: list[dict]
    account_events: list[dict]
    requests: list[dict]
    labels: dict[str, dict]
    closing_balances: dict[str, int]
    config: dict

    def fingerprint(self) -> str:
        data = [self.config, self.requests, [e.model_dump(mode="json") for e in self.events], self.labels]
        return sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()

    def save(self, directory: str | Path) -> dict:
        directory = Path(directory)
        (directory / "private").mkdir(parents=True, exist_ok=True)

        def write_rows(path, rows):
            with path.open("w", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")

        write_rows(directory / "accounts.jsonl", [dict(account_id=k, **v) for k, v in self.accounts.items()])
        write_rows(directory / "events.jsonl", [e.model_dump(mode="json") for e in self.events])
        write_rows(directory / "sessions.jsonl", self.sessions)
        write_rows(directory / "account_events.jsonl", self.account_events)
        write_rows(directory / "requests.jsonl", self.requests)
        write_rows(directory / "private" / "evaluation_labels.jsonl", [dict(transaction_id=k, **v) for k, v in self.labels.items()])
        (directory / "closing_balances.json").write_text(json.dumps(self.closing_balances, sort_keys=True), encoding="utf-8")
        manifest = dict(config=self.config, requests=len(self.requests), observations=len(self.events), labels=len(self.labels), prevalence=len(self.labels) / len(self.requests), fingerprint=self.fingerprint(), disclaimer="Fictitious data generated for one simulated PSP; not MIA transaction data")
        (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return manifest


def _scenario_specs(fraud_target: int):
    # At 10,000 requests this yields 60/10/10/20 labels in the four scored periods.
    full = []
    for day, count, cases in ((25, 4, 1), (45, 4, 1), (55, 4, 1), (65, 2, 1), (75, 2, 1), (90, 4, 1)):
        for case in range(cases):
            for kind in SCENARIOS:
                full.append((day, kind, count, case))
    # Small fixtures still contain each scenario. Pick in scenario order at test day.
    if fraud_target < 100:
        result = []
        remaining = fraud_target
        while remaining:
            for kind in SCENARIOS:
                if not remaining:
                    break
                result.append((90, kind, 1, len(result)))
                remaining -= 1
        return result
    repeat, remainder = divmod(fraud_target, 100)
    expanded = []
    for day, kind, size, _ in full:
        span = {25: 20, 45: 10, 55: 6, 65: 5, 75: 5, 90: 10}[day]
        for case in range(repeat):
            expanded.append((day + case % span, kind, size, case))
    for index in range(remainder):
        day, kind, _, _ = full[index % len(full)]
        expanded.append((day, kind, 1, repeat + index))
    return expanded


def generate(seed: int = 42, accounts: int = 400, attempts: int = 10000, days: int = 100, account_prefix: str = "A") -> GeneratedDataset:
    if accounts < 8 or attempts < 100 or days != 100:
        raise ValueError("Use at least 8 accounts, 100 attempts and the 100-day evaluation design")
    rng = random.Random(seed)
    account_ids = [f"{account_prefix}{i:04d}" for i in range(accounts)]
    account_data = {}
    for account_id in account_ids:
        amount = rng.randrange(1_000_000, 3_000_001)
        account_data[account_id] = dict(psp_id="LOCAL", opened_at=(START - timedelta(days=rng.randrange(15, 400))).isoformat(), initial_balance_bani=amount, balance_bani=amount)
    favorites = {account_id: rng.sample([a for a in account_ids if a != account_id], k=min(4, accounts - 1)) for account_id in account_ids}
    fraud_target = max(5, round(attempts * 0.01))
    specs = _scenario_specs(fraud_target)
    scenario_intents = []
    context_intents = []
    account_events = []
    for case_number, (day, kind, size, repeat) in enumerate(specs):
        sender = account_ids[(case_number * 7 + 3) % accounts]
        chain = [account_ids[(case_number * 7 + 3 + offset) % accounts] for offset in range(4)]
        base_time = START + timedelta(days=day - 1, hours=10 + case_number % 9, minutes=case_number % 43)
        scenario_id = f"SC-{case_number:03d}-{kind}"
        if kind == "account_takeover":
            account_events.append(dict(local_account_id=sender, event_type="password_reset", observed_at=(base_time - timedelta(minutes=20)).isoformat()))
            for index in range(5):
                context_intents.append(dict(kind="attempt_only", ts=base_time - timedelta(minutes=5 - index), sender=sender, receiver=f"EXT-A-{index}", amount=18000, psp="PSP-1"))
        if kind == "mule_flow":
            for index in range(5):
                context_intents.append(dict(kind="incoming", ts=base_time - timedelta(minutes=6 - index), sender=f"EXT-MULE-{case_number}-{index}", receiver=sender, amount=30000 + index * 3000, psp=f"PSP-{index % 3 + 1}"))
        if kind == "velocity":
            for index in range(5):
                context_intents.append(dict(kind="attempt_only", ts=base_time - timedelta(minutes=5 - index), sender=sender, receiver=f"EXT-V-{index}", amount=16000, psp="PSP-1"))
        for index in range(size):
            ts = base_time + (timedelta(hours=index * 2) if kind == "social_engineering" else timedelta(seconds=index * 35))
            actual_sender = chain[index % 4] if kind == "coordinated" else account_ids[(case_number * 7 + 3 + index) % accounts] if kind == "social_engineering" else sender
            receiver = chain[(index + 1) % 4] if kind == "coordinated" else (f"EXT-S-{case_number}-{index}" if kind in {"account_takeover", "social_engineering"} else f"EXT-R-{case_number}")
            receiver_psp = "LOCAL" if kind == "coordinated" else f"PSP-{index % 3 + 1}"
            amount = {"account_takeover": 60000, "mule_flow": 90000, "velocity": 17000, "social_engineering": 90000 if index < size - 1 else 13000, "coordinated": 25000}[kind] + rng.randrange(-3000, 3001)
            scenario_intents.append(dict(kind="outgoing", ts=ts, sender=actual_sender, receiver=receiver, psp=receiver_psp, amount=amount, device=f"NEW-{scenario_id}" if kind == "account_takeover" else f"MAIN-{actual_sender}", scenario_id=f"{scenario_id}-{index}" if kind == "social_engineering" else scenario_id, scenario_type=kind))
    if len(scenario_intents) > attempts:
        raise ValueError("Attempt count too small for configured scenarios")

    baseline_intents = []
    for index in range(attempts - len(scenario_intents)):
        day = index % days + 1
        sender = rng.choice(account_ids)
        hour = rng.randrange(8, 22) if rng.random() < 0.95 else rng.randrange(0, 24)
        ts = START + timedelta(days=day - 1, hours=hour, minutes=rng.randrange(60), seconds=rng.randrange(60))
        local = rng.random() < 0.68
        if local:
            receiver = rng.choice(favorites[sender]) if rng.random() < 0.87 else rng.choice([a for a in account_ids if a != sender])
            receiver_psp = "LOCAL"
        else:
            receiver = f"EXT-{rng.randrange(max(20, accounts // 2)):04d}"
            receiver_psp = f"PSP-{rng.randrange(1, 4)}"
        unusual = rng.random() < 0.008
        amount = int(min(110000, max(200, rng.lognormvariate(9.2, 0.65))))
        if unusual:
            amount *= 4
        device = f"UNUSUAL-{sender}-{index}" if unusual or rng.random() < 0.012 else f"MAIN-{sender}"
        baseline_intents.append(dict(kind="outgoing", ts=ts, sender=sender, receiver=receiver, psp=receiver_psp, amount=amount, device=device, legitimate_unusual=unusual))

    # Recurrent external salary-like inflows keep balances plausible.
    salary_intents = []
    for account_id in account_ids:
        for day in (1, 31, 61, 91):
            ts = START + timedelta(days=day - 1, hours=8, minutes=rng.randrange(60))
            salary_intents.append(dict(kind="incoming", ts=ts, sender=f"PAYROLL-{account_id}", receiver=account_id, amount=rng.randrange(110000, 260001), psp="PSP-1"))

    intents = baseline_intents + scenario_intents + context_intents + salary_intents
    intents.sort(key=lambda item: (item["ts"], {"incoming": 0, "attempt_only": 1, "outgoing": 2}[item["kind"]], item.get("sender", "")))
    balances = {account_id: data["initial_balance_bani"] for account_id, data in account_data.items()}
    sessions = [dict(session_id=f"INIT-{a}", local_account_id=a, device_id=f"MAIN-{a}", observed_at=(START - timedelta(days=1)).isoformat(), authentication_result="success") for a in account_ids]
    events = []
    requests = []
    labels = {}

    def event(transaction_id, when, event_type, sender, receiver, amount, sender_psp, receiver_psp, session_id=""):
        events.append(PaymentEvent(event_id=f"E{len(events):07d}", transaction_id=transaction_id, occurred_at=when, observed_at=when, event_type=event_type, sender_account_id=sender, receiver_account_id=receiver, sender_psp=sender_psp, receiver_psp=receiver_psp, amount_bani=amount, session_id=session_id))

    for item in intents:
        ts = item["ts"]
        if item["kind"] == "incoming":
            balances[item["receiver"]] += item["amount"]
            event(f"IN-{len(events):07d}", ts, "incoming", item["sender"], item["receiver"], item["amount"], item["psp"], "LOCAL")
            continue
        if item["kind"] == "attempt_only":
            event(f"CTX-{len(events):07d}", ts, "attempt", item["sender"], item["receiver"], item["amount"], "LOCAL", item["psp"])
            continue
        sender = item["sender"]
        if balances[sender] < 100:
            topup = 50000
            balances[sender] += topup
            event(f"TOPUP-{len(events):07d}", ts - timedelta(seconds=2), "incoming", f"PAYROLL-{sender}", sender, topup, "PSP-1", "LOCAL")
        amount = min(item["amount"], balances[sender])
        transaction_id = f"T{len(requests):07d}"
        session_id = f"S-{transaction_id}"
        sessions.append(dict(session_id=session_id, local_account_id=sender, device_id=item["device"], observed_at=ts.isoformat(), authentication_result="success"))
        request = dict(transaction_id=transaction_id, sender_account_id=sender, receiver_account_id=item["receiver"], receiver_psp=item["psp"], amount_bani=amount, currency="MDL", session_id=session_id, device_id=item["device"], initiation_method="APP", occurred_at=ts.isoformat(), split=split_for_day((ts - START).days + 1), legitimate_unusual=bool(item.get("legitimate_unusual", False)))
        requests.append(request)
        if "scenario_id" in item:
            labels[transaction_id] = dict(scenario_id=item["scenario_id"], scenario_type=item["scenario_type"], is_simulated_fraud=True)
        event(transaction_id, ts, "attempt", sender, item["receiver"], amount, "LOCAL", item["psp"], session_id)
        balances[sender] -= amount
        if item["psp"] == "LOCAL":
            balances[item["receiver"]] += amount
        event(transaction_id, ts + timedelta(seconds=1), "completed", sender, item["receiver"], amount, "LOCAL", item["psp"], session_id)
    events.sort(key=lambda e: (e.observed_at, e.event_id))
    config = dict(seed=seed, accounts=accounts, attempts=attempts, days=days, account_prefix=account_prefix, start=START.isoformat(), external_psps=["PSP-1", "PSP-2", "PSP-3"], generator_version="generator-v1", scenario_count=len(labels))
    return GeneratedDataset(account_data, events, sessions, account_events, requests, labels, balances, config)
