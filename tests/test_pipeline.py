import csv
import tempfile

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from core.models import Account, Assessment, DatasetImport, DetectionRun, FraudCase, Transaction
from core.services import analyze, assess_transfer, import_dataset
from detection.algorithms import DBSCAN, IsolationForest, LocalOutlierFactor
from detection.features import build
from detection.pipeline import contributions, parameters


class ReliableWorkflowTests(TestCase):
    def setUp(self):
        self.a = Account.objects.create(id='SIM_A')
        self.b = Account.objects.create(id='SIM_B')
        Transaction.objects.bulk_create([
            Transaction(id=f'SIM_{i:04}', sender=self.a, recipient=self.b,
                        amount=100 + i % 5, timestamp=i * 400, kind='TRANSFER',
                        origin='Generated scenario', currency='DEMO_UNIT', device='D', truth=False)
            for i in range(205)
        ])

    def test_manual_transfer_matches_replay_without_reassessing_history(self):
        analyze(trees=8)
        original = list(Transaction.objects.values_list('pk', 'decision', 'risk'))
        previous_assessments = Assessment.objects.count()
        tx = Transaction.objects.create(id='LIVE_TEST', sender=self.a, recipient=self.b,
                                        amount=9000, timestamp=90000, kind='TRANSFER',
                                        origin='Generated scenario', currency='DEMO_UNIT',
                                        device='NEW_DEVICE', failed_logins=4, truth=None)
        result = assess_transfer(tx)
        self.assertEqual(Assessment.objects.count(), previous_assessments + 1)
        self.assertEqual(result.run.count, 1)
        self.assertEqual(result.split, 'manual')
        self.assertIsNone(tx.truth)
        self.assertEqual(original, list(Transaction.objects.exclude(pk=tx.pk).values_list('pk', 'decision', 'risk')))
        replay = analyze(trees=8)
        repeated = Assessment.objects.get(run=replay, transaction=tx)
        self.assertEqual((result.forest, result.lof, result.cluster, result.risk),
                         (repeated.forest, repeated.lof, repeated.cluster, repeated.risk))
        self.assertEqual(replay.metrics['Generated scenario']['methods']['test']['Combined']['n'], 13)

    def test_batch_replay_avoids_per_transfer_queries(self):
        with CaptureQueriesContext(connection) as queries:
            run = analyze(trees=8)
        self.assertLess(len(queries), 40)
        self.assertEqual(run.count, 77)

    def test_small_source_rolls_back_entire_run(self):
        Transaction.objects.create(id='P', sender=self.a, recipient=self.b, amount=10,
                                   timestamp=1, kind='TRANSFER', origin='PaySim',
                                   currency='PAYSIM_UNIT', device='D')
        with self.assertRaises(ValueError):
            analyze(trees=8)
        self.assertFalse(DetectionRun.objects.exists())
        self.assertFalse(Assessment.objects.exists())
        self.assertFalse(FraudCase.objects.exists())
        self.assertFalse(Transaction.objects.exclude(decision='Pending').exists())

    def test_filtered_export_and_romanian_pages(self):
        user = User.objects.create_user('analyst')
        self.client.force_login(user)
        export = self.client.get('/export/?q=SIM_0204')
        self.assertEqual(len(export.content.decode().splitlines()), 2)
        self.assertContains(self.client.get('/'), 'Cazuri active')
        analyze(trees=8)
        page = self.client.get('/algorithms/')
        self.assertContains(page, 'Rezultate pe datele de test')
        self.assertNotContains(page, 'Cum se formează decizia?')
        self.assertNotContains(page, 's(x)')


class ImportValidationTests(TestCase):
    def test_invalid_values_leave_database_untouched(self):
        valid = dict(transaction_id='T', nameOrig='A', nameDest='B', amount='10.00',
                     timestamp_seconds='0', device_id='D', ground_truth_fraud='0',
                     currency='DEMO_UNIT', data_origin='Generated scenario',
                     failed_login_attempts='0', type='TRANSFER')
        for invalid in [{'amount': 'NaN'}, {'amount': '0.001'}, {'nameOrig': ''},
                        {'timestamp_seconds': '-1'}, {'data_origin': 'Unknown'},
                        {'currency': 'MDL'}, {'transaction_id': 'x' * 81}]:
            with self.subTest(invalid=invalid), tempfile.NamedTemporaryFile(mode='w+', suffix='.csv') as file:
                writer = csv.DictWriter(file, fieldnames=valid)
                writer.writeheader()
                writer.writerow(valid)
                writer.writerow({**valid, 'transaction_id': 'BAD', **invalid})
                file.flush()
                with self.assertRaises(ValueError):
                    import_dataset(file.name)
                self.assertFalse(Transaction.objects.exists())
                self.assertFalse(Account.objects.exists())
                self.assertFalse(DatasetImport.objects.exists())

    def test_empty_analysis_does_not_create_run(self):
        with self.assertRaises(ValueError):
            analyze()
        self.assertFalse(DetectionRun.objects.exists())


class NumericalPolicyTests(TestCase):
    def test_contributions_have_a_checkable_total(self):
        parts = contributions(.55, 2, -1, 50)
        self.assertAlmostEqual(sum(part['points'] for part in parts), 57.5)
        self.assertEqual(round(sum(part['points'] for part in parts)), 58)
        self.assertEqual(sum(p['points'] for p in contributions(1, 999, -1, 100)), 100)

    def test_invalid_parameters_and_score_shapes(self):
        for kwargs in [{'eps': float('nan')}, {'trees': 0}, {'k': 31}]:
            with self.assertRaises(ValueError):
                parameters(**kwargs)
        for model in [IsolationForest(), LocalOutlierFactor()]:
            with self.assertRaises(ValueError):
                model.score([0])
            model.fit([[0], [1]])
            with self.assertRaises(ValueError):
                model.score([0, 1])
        with self.assertRaises(ValueError):
            DBSCAN(float('nan'))

    def test_features_reject_unsorted_history(self):
        from types import SimpleNamespace
        rows = [SimpleNamespace(sender_id='A', recipient_id='B', timestamp=t,
                                amount=1, device='D', failed_logins=0) for t in [10, 0]]
        with self.assertRaises(ValueError):
            build(rows)
