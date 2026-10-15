from django.contrib.auth.models import User
from django.test import TestCase

from core.background import enqueue_transfer, process_next
from core.demo import fictional_name, prepare_profiles
from core.models import Account, AnalysisJob, Assessment, FraudCase, Transaction
from core.services import analyze
from detection.forecast import estimate


class BackgroundTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('analyst', password='test')
        self.a = Account.objects.create(id='SIM_A', display_name='Ion Rusu')
        self.b = Account.objects.create(id='SIM_B', display_name='Maria Popa')
        Transaction.objects.bulk_create([
            Transaction(id=f'SIM_{i:04}', sender=self.a, recipient=self.b, amount=100 + i % 5,
                        timestamp=i * 400, kind='TRANSFER', origin='Generated scenario',
                        currency='DEMO_UNIT', device='D', truth=False)
            for i in range(205)])
        analyze(trees=8)
        self.client.force_login(self.user)

    def test_request_returns_before_scoring_and_worker_finishes_it(self):
        previous = Assessment.objects.count()
        response = self.client.post('/simulate/', {'sender': self.a.pk, 'recipient': self.b.pk,
                                                   'amount': '500', 'device': 'NEW', 'failed_logins': 4})
        self.assertEqual(response.status_code, 302)
        tx = Transaction.objects.get(id__startswith='LIVE_')
        self.assertEqual(tx.decision, 'Pending')
        self.assertEqual(Assessment.objects.count(), previous)
        self.assertEqual(self.client.get(f'/analysis/status/{tx.pk}/').json()['status'], 'queued')
        self.assertTrue(process_next())
        tx.refresh_from_db()
        self.assertNotEqual(tx.decision, 'Pending')
        self.assertEqual(Assessment.objects.count(), previous + 1)
        self.assertEqual(self.client.get(f'/analysis/status/{tx.pk}/').json()['status'], 'completed')
        self.assertFalse(process_next())
        self.assertIsNone(tx.truth)

    def test_queued_requests_exclude_later_requests(self):
        first = Transaction.objects.create(id='LIVE_A', sender=self.a, recipient=self.b, amount=200,
                                           timestamp=90000, kind='TRANSFER', origin='Generated scenario',
                                           currency='DEMO_UNIT', device='NEW', truth=None)
        enqueue_transfer(first, self.user)
        second = Transaction.objects.create(id='LIVE_B', sender=self.a, recipient=self.b, amount=300,
                                            timestamp=90010, kind='TRANSFER', origin='Generated scenario',
                                            currency='DEMO_UNIT', device='NEW', truth=None)
        enqueue_transfer(second, self.user)
        process_next()
        self.assertEqual(Assessment.objects.filter(transaction=first).count(), 1)
        self.assertFalse(Assessment.objects.filter(transaction=second).exists())
        process_next()
        self.assertEqual(Assessment.objects.filter(transaction=second).count(), 1)
        self.assertEqual(AnalysisJob.objects.filter(status='completed').count(), 2)

    def test_failure_rolls_back_and_does_not_stop_next_job(self):
        bad = Transaction.objects.create(id='BAD', sender=self.a, recipient=self.b, amount=1, timestamp=1,
                                        kind='TRANSFER', origin='PaySim', currency='PAYSIM_UNIT', device='D')
        enqueue_transfer(bad)
        self.assertTrue(process_next())
        self.assertEqual(AnalysisJob.objects.get(transaction=bad).status, 'failed')
        self.assertFalse(Assessment.objects.filter(transaction=bad).exists())

    def test_profiles_preserve_existing_names_and_notes(self):
        prepare_profiles()
        self.a.refresh_from_db()
        self.assertEqual(self.a.display_name, 'Ion Rusu')
        self.assertEqual(fictional_name('SIM_X'), fictional_name('SIM_X'))
        self.assertNotEqual(fictional_name('SIM_X'), 'SIM_X')
        self.assertContains(self.client.get('/accounts/?q=Ion'), 'Ion Rusu')
        profile = self.client.get('/accounts/SIM_A/')
        self.assertContains(profile, 'Istoricul tranzacțiilor')
        self.assertContains(profile, 'Estimarea alertelor')
        self.assertNotContains(self.client.get('/'), 'Estimarea alertelor')

    def test_results_have_no_run_controls(self):
        self.user.is_staff = True
        self.user.save()
        response = self.client.get('/algorithms/')
        self.assertNotContains(response, 'name="trees"')
        self.assertNotContains(response, 'Analizează datele')


class ForecastTests(TestCase):
    def test_weighted_alert_counts_and_future_exclusion(self):
        rows = [(100, 90), (3700, 50), (7200, 70), (9000, 80)]
        result = estimate(rows, now=7200, hours=2)
        # First bucket has one alert; last has two. Future observation is ignored.
        self.assertEqual(result['observed_transfers'], 3)
        self.assertEqual(result['observed_alerts'], 3)
        self.assertEqual(result['expected'], 1.7)
        self.assertEqual(estimate([], now=7200)['expected'], 0)
