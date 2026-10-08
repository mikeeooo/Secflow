"""Prepare a reproducible PaySim-based local dataset using only Python's stdlib."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from itertools import islice
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIELDS = [
    'step', 'type', 'amount', 'nameOrig', 'oldbalanceOrg', 'newbalanceOrig',
    'nameDest', 'oldbalanceDest', 'newbalanceDest', 'isFraud', 'isFlaggedFraud',
]
EXTRA_FIELDS = [
    'transaction_id', 'source_row_id', 'timestamp_seconds', 'device_id',
    'is_new_device', 'session_id', 'login_attempts', 'failed_login_attempts',
    'data_origin', 'security_metadata_origin', 'timestamp_origin',
    'scenario_type', 'scenario_id', 'ground_truth_fraud', 'currency',
]
FIELDS = SOURCE_FIELDS + EXTRA_FIELDS
SCENARIOS = (
    'unusual_amount', 'repeated_transfers', 'amount_fragmentation',
    'account_takeover', 'mule_account', 'suspicious_beneficiary',
    'coordinated_activity', 'scam_related_transfer',
    'legitimate_large_payment', 'legitimate_new_device', 'legitimate_burst',
)


def checksum(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def stable_rng(seed, key):
    digest = hashlib.sha256(f'{seed}:{key}'.encode()).digest()
    return random.Random(int.from_bytes(digest[:8], 'big'))


def write_csv(path, fields, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def source_rows(path, limit, seed):
    rows = []
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or []) != set(SOURCE_FIELDS):
            raise ValueError('Unexpected PaySim schema; original 11 columns required.')
        for index, raw in enumerate(islice(reader, limit), 1):
            if int(raw['step']) < 1 or not math.isfinite(float(raw['amount'])) or float(raw['amount']) < 0:
                raise ValueError(f'Invalid PaySim row {index}')
            if raw['isFraud'] not in ('0', '1'):
                raise ValueError(f'Invalid label at row {index}')
            row = dict(raw)
            row.update({
                'transaction_id': f'PS_{index:09d}', 'source_row_id': index,
                'data_origin': 'PaySim', 'scenario_type': 'source_unclassified',
                'scenario_id': '', 'ground_truth_fraud': int(raw['isFraud']),
                'currency': 'PAYSIM_UNIT', 'timestamp_origin': 'Generated within source hour',
                'security_metadata_origin': 'Generated independently of source fraud label',
            })
            rows.append(row)
    if not rows:
        raise ValueError('The input has no transactions.')
    # Label-independent, monotonic timestamps within each original hour.
    hours = defaultdict(list)
    for row in rows:
        hours[int(row['step'])].append(row)
    for hour, group in sorted(hours.items()):
        rng = stable_rng(seed, f'hour:{hour}')
        offsets = sorted(rng.randrange(3600) for _ in group)
        for row, offset in zip(group, offsets):
            row['timestamp_seconds'] = (hour - 1) * 3600 + offset
    return rows


def generated_rows(start, repeats, seed):
    rng = stable_rng(seed, 'scenarios')
    events = []

    def event(sender, recipient, amount, when, scenario, episode, fraud=0, new=False, failures=None):
        row = {field: '' for field in SOURCE_FIELDS}
        row.update({
            'step': when // 3600 + 1, 'type': 'TRANSFER', 'amount': f'{amount:.2f}',
            'nameOrig': sender, 'nameDest': recipient, 'isFraud': fraud,
            'isFlaggedFraud': 0, 'source_row_id': '', 'timestamp_seconds': when,
            'data_origin': 'Generated scenario', 'scenario_type': scenario,
            'scenario_id': episode, 'ground_truth_fraud': fraud,
            'currency': 'DEMO_UNIT', 'timestamp_origin': 'Generated scenario timeline',
            'security_metadata_origin': 'Generated scenario metadata',
            '_device_variant': 'NEW' if new else 'PRIMARY', '_failures': failures,
        })
        events.append(row)

    for kind_index, kind in enumerate(SCENARIOS):
        for rep in range(repeats):
            episode = f'{kind}_{rep + 1:02d}'
            account = f'SIM_{kind_index:02d}_{rep:02d}'
            friend = f'{account}_FAMILIAR'
            target = f'{account}_NEW_RECIPIENT'
            # Separate episodes with their own accounts; normal history comes first.
            episode_start = start + rep * 120
            for h in range(30):
                event(account, friend, rng.uniform(80, 300), episode_start + h * 14400,
                      'normal_history', episode, failures=0)
            attack = episode_start + 30 * 14400
            if kind == 'unusual_amount':
                event(account, friend, rng.uniform(8000, 15000), attack, kind, episode, 1)
            elif kind == 'repeated_transfers':
                for j in range(12):
                    event(account, target, rng.uniform(700, 900), attack + j * 4, kind, episode, 1)
            elif kind == 'amount_fragmentation':
                for j in range(15):
                    event(account, target, rng.uniform(180, 240), attack + j * 7, kind, episode, 1)
            elif kind == 'account_takeover':
                for j in range(3):
                    event(account, target, rng.uniform(5000, 8000), attack + j * 12,
                          kind, episode, 1, new=True, failures=7 if j == 0 else 0)
            elif kind == 'mule_account':
                incoming = []
                for j in range(6):
                    sender = f'{account}_FUNDER_{j}'
                    for h in range(6):
                        event(sender, f'{sender}_FAMILIAR', rng.uniform(80, 300),
                              episode_start + h * 14400, 'normal_history', episode, failures=0)
                    amount = round(rng.uniform(1000, 1600), 2)
                    incoming.append(amount)
                    event(sender, account, amount, attack + j * 5, kind, episode, 1)
                event(account, target, sum(incoming) * 0.98, attack + 40, kind, episode, 1)
            elif kind == 'suspicious_beneficiary':
                for j in range(3):
                    event(account, target, rng.uniform(2000, 3000), attack + j * 10, kind, episode, 1)
            elif kind == 'coordinated_activity':
                senders = [account] + [f'{account}_PARTNER_{j}' for j in range(3)]
                for sender in senders[1:]:
                    for h in range(6):
                        event(sender, f'{sender}_FAMILIAR', rng.uniform(80, 300),
                              episode_start + h * 14400, 'normal_history', episode, failures=0)
                for j in range(16):
                    event(senders[j % 4], target, 2450 + rng.uniform(-20, 20),
                          attack + j * 3, kind, episode, 1)
            elif kind == 'scam_related_transfer':
                event(account, target, rng.uniform(6000, 9000), attack, kind, episode, 1)
            elif kind == 'legitimate_large_payment':
                event(account, friend, rng.uniform(8000, 15000), attack, kind, episode)
            elif kind == 'legitimate_new_device':
                event(account, friend, rng.uniform(80, 300), attack, kind, episode, new=True, failures=0)
            elif kind == 'legitimate_burst':
                for j in range(8):
                    event(account, friend, rng.uniform(80, 300), attack + j * 5, kind, episode, failures=0)
    events.sort(key=lambda row: (row['timestamp_seconds'], row['scenario_id'], row['nameOrig']))
    for index, row in enumerate(events, 1):
        row['transaction_id'] = f'SIM_{index:09d}'
    return events


def add_security_metadata(rows, seed):
    """Build causal device history. PaySim labels never control metadata generation."""
    seen = defaultdict(set)
    for row in rows:
        rng = stable_rng(seed, row['transaction_id'])
        account = row['nameOrig']
        if row['data_origin'] == 'PaySim':
            # Most accounts reuse a primary device; occasional alternatives are independent of labels.
            variant = 'PRIMARY' if rng.random() < 0.98 else f'ALT_{rng.randrange(1, 4)}'
            failures = rng.choices([0, 1, 2, 3, 5], weights=[92, 5, 2, 0.8, 0.2])[0]
        else:
            variant = row.pop('_device_variant')
            failures = row.pop('_failures')
            if failures is None:
                failures = rng.choices([0, 1, 2], weights=[96, 3, 1])[0]
        device = 'DEV_' + hashlib.sha256(f'{account}:{variant}'.encode()).hexdigest()[:20]
        row.update({
            'device_id': device, 'is_new_device': int(device not in seen[account]),
            'session_id': f"SESSION_{row['transaction_id']}",
            'failed_login_attempts': failures, 'login_attempts': failures + 1,
        })
        seen[account].add(device)


def validate(rows):
    ids = set()
    seen = defaultdict(set)
    previous = -1
    for row in rows:
        tx = row['transaction_id']
        if tx in ids:
            raise ValueError(f'Duplicate ID: {tx}')
        ids.add(tx)
        timestamp = int(row['timestamp_seconds'])
        if timestamp < previous:
            raise ValueError('Transactions are not chronological.')
        previous = timestamp
        if not (0 <= int(row['failed_login_attempts']) < int(row['login_attempts'])):
            raise ValueError('Invalid authentication counts.')
        expected_new = int(row['device_id'] not in seen[row['nameOrig']])
        if int(row['is_new_device']) != expected_new:
            raise ValueError('Device flag disagrees with previous history.')
        seen[row['nameOrig']].add(row['device_id'])
        if row['data_origin'] == 'PaySim':
            if timestamp // 3600 + 1 != int(row['step']):
                raise ValueError('Timestamp outside source hour.')
        if float(row['amount']) <= 0 or not math.isfinite(float(row['amount'])):
            raise ValueError('Invalid amount.')


def related_tables(rows):
    accounts, devices = {}, {}
    logins = []
    for row in rows:
        time = int(row['timestamp_seconds'])
        for role, account in [('sender', row['nameOrig']), ('recipient', row['nameDest'])]:
            if account not in accounts:
                accounts[account] = {
                    'account_id': account, 'data_origin': row['data_origin'],
                    'currency': row['currency'], 'first_observed_seconds': time,
                    'last_observed_seconds': time, 'sent_count': 0, 'received_count': 0,
                }
            item = accounts[account]
            item['last_observed_seconds'] = time
            item['sent_count' if role == 'sender' else 'received_count'] += 1
        key = (row['nameOrig'], row['device_id'])
        if key not in devices:
            devices[key] = {
                'account_id': key[0], 'device_id': key[1], 'first_seen_seconds': time,
                'last_seen_seconds': time, 'metadata_origin': row['security_metadata_origin'],
            }
        devices[key]['last_seen_seconds'] = time
        for attempt in range(int(row['login_attempts'])):
            # All attempts occur by the transfer time; equal second is permitted.
            logins.append({
                'authentication_id': f"AUTH_{row['transaction_id']}_{attempt + 1}",
                'session_id': row['session_id'], 'transaction_id': row['transaction_id'],
                'account_id': row['nameOrig'], 'device_id': row['device_id'],
                'timestamp_seconds': max(0, time - int(row['failed_login_attempts']) + attempt),
                'result': 'Success' if attempt == int(row['failed_login_attempts']) else 'Failed',
                'metadata_origin': row['security_metadata_origin'],
            })
    logins.sort(key=lambda row: (row['timestamp_seconds'], row['authentication_id']))
    return list(accounts.values()), list(devices.values()), logins


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'data/raw/PS_20174392719_1491204439457_log.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/generated')
    parser.add_argument('--limit', type=int, default=50000, help='Contiguous chronological prefix of PaySim.')
    parser.add_argument('--repeats', type=int, default=10, help='Episodes per generated scenario.')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    if args.limit < 1 or args.repeats < 1:
        parser.error('--limit and --repeats must be positive')
    source = source_rows(args.source, args.limit, args.seed)
    synthetic = generated_rows(max(row['timestamp_seconds'] for row in source) + 3600,
                               args.repeats, args.seed)
    combined = sorted(source + synthetic, key=lambda row: (row['timestamp_seconds'], row['transaction_id']))
    add_security_metadata(combined, args.seed)
    validate(combined)
    accounts, devices, logins = related_tables(combined)
    args.output.mkdir(parents=True, exist_ok=True)
    files = {
        'secflow_transactions.csv': (FIELDS, combined),
        'paysim_extended.csv': (FIELDS, source),
        'generated_scenarios.csv': (FIELDS, synthetic),
        'accounts.csv': (list(accounts[0]), accounts),
        'devices.csv': (list(devices[0]), devices),
        'authentication_events.csv': (list(logins[0]), logins),
    }
    for name, (fields, records) in files.items():
        write_csv(args.output / name, fields, records)
    manifest = {
        'schema_version': 1, 'generator_version': 1, 'seed': args.seed,
        'source': {'name': args.source.name, 'url': 'https://www.kaggle.com/datasets/ealaxi/paysim1/data',
                   'sha256': checksum(args.source), 'license': 'CC BY-SA 4.0',
                   'selection': 'Contiguous prefix, original row order; no class balancing',
                   'requested_rows': args.limit, 'selected_rows': len(source),
                   'step_range': [min(int(r['step']) for r in source), max(int(r['step']) for r in source)]},
        'counts': {'transactions': len(combined), 'paysim': len(source), 'generated': len(synthetic),
                   'accounts': len(accounts), 'devices': len(devices), 'authentication_events': len(logins)},
        'source_fraud_count': sum(int(r['isFraud']) for r in source),
        'generated_fraud_count': sum(int(r['ground_truth_fraud']) for r in synthetic),
        'generated_scenario_counts': dict(sorted(Counter(r['scenario_type'] for r in synthetic).items())),
        'episodes_per_scenario': args.repeats,
        'time_range_seconds': [combined[0]['timestamp_seconds'], combined[-1]['timestamp_seconds']],
        'feature_exclusions': ['isFraud', 'isFlaggedFraud', 'ground_truth_fraud', 'scenario_type',
                               'scenario_id', 'data_origin', 'security_metadata_origin', 'timestamp_origin',
                               'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest'],
        'notes': [
            'PaySim second-level timing and security information are generated, not source observations.',
            'Devices are account-specific; first observation is marked new even for legitimate activity.',
            'PaySim and generated scenarios use separate account namespaces and currency units.',
            'Scenario labels encode the generator narrative, not confirmed real-world fraud.',
            'PaySim metadata generation is independent of its fraud labels.',
            'Source and generated evaluations must be reported separately.',
            'A prefix is a local working subset, not a representative full-month benchmark.',
        ],
        'outputs': {name: {'rows': len(records), 'sha256': checksum(args.output / name)}
                    for name, (_, records) in files.items()},
    }
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'counts': manifest['counts'], 'source_fraud': manifest['source_fraud_count'],
                      'generated_fraud': manifest['generated_fraud_count'],
                      'step_range': manifest['source']['step_range']}, indent=2))


if __name__ == '__main__':
    main()
