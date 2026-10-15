"""Small deterministic MIA-style portfolio. Entirely synthetic, never relabels PaySim."""
import csv
import hashlib
import json
import math
import random
from pathlib import Path

ORIGIN = 'MIA demo'
REFERENCE = 256
VALIDATION = 256
HISTORY = 1280
STREAM = 240
SEED = 73
FIELDS = ['transaction_id', 'nameOrig', 'nameDest', 'amount', 'timestamp_seconds', 'device_id',
          'ground_truth_fraud', 'currency', 'data_origin', 'failed_login_attempts', 'type',
          'scenario_type', 'phase']


def generate(seed=SEED):
    rng = random.Random(seed)
    clients = [f'SIM_MIA_{i:03}' for i in range(36)]
    receivers = [f'SIM_MIA_{i:03}' for i in range(36, 48)]
    rows = []
    timestamp = 0
    burst_sender, burst_left = None, 0
    for i in range(HISTORY + STREAM):
        phase = 'reference' if i < REFERENCE else 'validation' if i < REFERENCE + VALIDATION else 'history' if i < HISTORY else 'stream'
        # Only reference is normal by design. Validation/test use the same scenario recipe with fresh draws.
        choice = rng.random() if phase != 'reference' else 1
        scenario = 'ordinary'
        sender = clients[i % len(clients)] if phase == 'reference' else rng.choice(clients)
        recipient = receivers[int(sender[-3:]) % len(receivers)]
        amount = round(math.exp(rng.gauss(math.log(550 + (int(sender[-3:]) % 4) * 250), .48)), 2)
        failures = 1 if rng.random() < .06 else 0
        device = f'DEV_{sender}_MAIN'
        fraud = False
        if burst_left:
            sender = burst_sender
            recipient = rng.choice(receivers)
            scenario = 'rapid_sequence'
            amount = round(rng.uniform(1400, 3200), 2)
            failures = rng.randrange(3, 6)
            device = f'DEV_{sender}_SESSION_{i // 8}'
            fraud = True
            burst_left -= 1
            timestamp += rng.randint(2, 8)
        else:
            timestamp += rng.randint(30, 80)
            if choice < .035:
                scenario, fraud = 'unusual_amount', True
                amount = round(rng.uniform(16000, 35000), 2)
            elif choice < .075:
                scenario, fraud = 'new_device_access', True
                failures = rng.randrange(4, 8)
                device = f'DEV_{sender}_UNKNOWN_{i}'
                amount = round(rng.uniform(4500, 11000), 2)
            elif choice < .095:
                scenario, fraud = 'rapid_sequence', True
                burst_sender, burst_left = sender, 5
                failures, amount = 4, round(rng.uniform(1400, 3200), 2)
                device = f'DEV_{sender}_SESSION_{i // 8}'
            elif choice < .145:
                # Legitimate unusual payments create meaningful false-positive examples.
                scenario = 'legitimate_large'
                amount = round(rng.uniform(3000, 6500), 2)
            elif choice < .20:
                scenario = 'legitimate_new_device'
                device = f'DEV_{sender}_SECOND'
                recipient = rng.choice(receivers)
        rows.append(dict(zip(FIELDS, [f'MIA_{i:06}', sender, recipient, f'{amount:.2f}', timestamp,
                    device, int(fraud), 'MDL', ORIGIN, failures, 'TRANSFER', scenario, phase])))
    return rows


def write_dataset(directory, seed=SEED):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'mia_demo.csv'
    rows = generate(seed)
    with path.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    manifest = {'name': 'Synthetic MIA presentation portfolio', 'seed': seed, 'rows': len(rows),
                'reference': REFERENCE, 'validation': VALIDATION, 'history': HISTORY, 'stream': STREAM,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'provenance': 'Entirely synthetic; amounts in demonstration MDL; no real MIA data',
                'labels': 'Scenario truth used only for validation/evaluation, never as detection features'}
    (directory / 'mia_demo_manifest.json').write_text(json.dumps(manifest, indent=2))
    return path
