"""Check chronology, labels, authentication relationships and reproducibility."""
import copy
import csv
import json
import unittest
from collections import Counter
from pathlib import Path

from datasets.prepare_dataset import (
    ROOT, SCENARIOS, add_security_metadata, checksum, generated_rows,
    related_tables, source_rows, validate,
)


class DatasetTests(unittest.TestCase):
    def test_generated_scenarios_are_reproducible(self):
        a = generated_rows(3600, 2, 42)
        b = generated_rows(3600, 2, 42)
        self.assertEqual(a, b)
        self.assertNotEqual(a, generated_rows(3600, 2, 43))
        add_security_metadata(a, 42)
        validate(a)
        kinds = {r['scenario_type'] for r in a}
        self.assertTrue(set(SCENARIOS).issubset(kinds))
        for row in a:
            if row['scenario_type'].startswith('legitimate') or row['scenario_type'] == 'normal_history':
                self.assertEqual(row['ground_truth_fraud'], 0)
            else:
                self.assertEqual(row['ground_truth_fraud'], 1)

    def test_paysim_security_and_time_do_not_depend_on_labels(self):
        raw = next((ROOT / 'data/raw').glob('*.csv'))
        a = source_rows(raw, 1000, 42)
        b = copy.deepcopy(a)
        for row in b:
            row['isFraud'] = 1 - int(row['isFraud'])
            row['ground_truth_fraud'] = row['isFraud']
        add_security_metadata(a, 42)
        add_security_metadata(b, 42)
        for left, right in zip(a, b):
            for field in ('timestamp_seconds', 'device_id', 'is_new_device',
                          'login_attempts', 'failed_login_attempts', 'session_id'):
                self.assertEqual(left[field], right[field])

    def test_authentication_events_are_linked_and_causal(self):
        rows = generated_rows(0, 1, 42)
        add_security_metadata(rows, 42)
        validate(rows)
        accounts, devices, logins = related_tables(rows)
        index = {r['transaction_id']: r for r in rows}
        attempts = Counter()
        failures = Counter()
        for login in logins:
            transaction = index[login['transaction_id']]
            self.assertLessEqual(login['timestamp_seconds'], transaction['timestamp_seconds'])
            self.assertEqual(login['device_id'], transaction['device_id'])
            attempts[login['transaction_id']] += 1
            failures[login['transaction_id']] += login['result'] == 'Failed'
        for tx, row in index.items():
            self.assertEqual(attempts[tx], row['login_attempts'])
            self.assertEqual(failures[tx], row['failed_login_attempts'])
        self.assertEqual(sum(a['sent_count'] for a in accounts), len(rows))
        self.assertEqual(sum(a['received_count'] for a in accounts), len(rows))
        self.assertEqual(len(devices), len({(r['nameOrig'], r['device_id']) for r in rows}))

    def test_exported_files_match_manifest_and_original_rows(self):
        directory = ROOT / 'data/generated'
        manifest = json.loads((directory / 'manifest.json').read_text())
        for name, metadata in manifest['outputs'].items():
            self.assertEqual(checksum(directory / name), metadata['sha256'])
            with (directory / name).open() as stream:
                self.assertEqual(sum(1 for _ in csv.DictReader(stream)), metadata['rows'])
        with (directory / 'secflow_transactions.csv').open() as stream:
            combined = list(csv.DictReader(stream))
        validate(combined)
        raw = next((ROOT / 'data/raw').glob('*.csv'))
        with raw.open() as source, (directory / 'paysim_extended.csv').open() as prepared:
            for original, extended in zip(csv.DictReader(source), csv.DictReader(prepared)):
                for field, value in original.items():
                    self.assertEqual(value, extended[field])

    def test_mule_outflow_has_preceding_incoming_funds(self):
        rows = generated_rows(3600, 1, 42)
        mule = [r for r in rows if r['scenario_type'] == 'mule_account']
        outgoing = mule[-1]
        incoming = [r for r in mule if r['nameDest'] == outgoing['nameOrig']]
        self.assertEqual(len(incoming), 6)
        self.assertTrue(all(r['timestamp_seconds'] < outgoing['timestamp_seconds'] for r in incoming))
        self.assertAlmostEqual(sum(float(r['amount']) for r in incoming) * 0.98,
                               float(outgoing['amount']), places=2)


if __name__ == '__main__':
    unittest.main()
