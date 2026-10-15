import tempfile
from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import TestCase, SimpleTestCase
from django.utils import timezone

from core.background import process_next
from core.models import AnalysisJob, Assessment, DemoPlayback, FraudCase, Transaction
from core.playback import repeat_stream, tick
from core.services import analyze, import_dataset
from datasets.demo_mia import generate, write_dataset, HISTORY, ORIGIN
from detection.features import build
from detection.mia import fit


class DatasetRecipeTests(SimpleTestCase):
    def test_reproducibility_and_no_test_label_leakage(self):
        rows = generate()
        self.assertEqual(rows, generate())
        self.assertEqual(len(rows), 1520)
        self.assertEqual(sum(row['phase'] == 'reference' for row in rows), 256)
        self.assertTrue(all(not row['ground_truth_fraud'] for row in rows[:256]))
        self.assertTrue(any(row['scenario_type'].startswith('legitimate_') for row in rows))
        features = build([SimpleNamespace(sender_id=row['nameOrig'], recipient_id=row['nameDest'],
                                          amount=row['amount'], timestamp=row['timestamp_seconds'],
                                          device=row['device_id'], failed_logins=row['failed_login_attempts']) for row in rows])
        labels = [bool(row['ground_truth_fraud']) for row in rows]
        first = fit(features, labels)[2]['thresholds']
        changed = labels[:512] + [not label for label in labels[512:]]
        self.assertEqual(first, fit(features, changed)[2]['thresholds'])


class PlaybackTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('analyst')
        with tempfile.TemporaryDirectory() as folder:
            import_dataset(write_dataset(folder))
        cls.demo_run = analyze(origin=ORIGIN)
        DemoPlayback.objects.create(pk=1, status='paused')

    def setUp(self):
        self.client.force_login(self.user)

    def test_future_rows_hidden_and_only_released_transfer_is_scored(self):
        self.assertEqual(Transaction.objects.filter(visible=True).count(), HISTORY)
        self.assertFalse(Assessment.objects.filter(transaction__visible=False).exists())
        future = Transaction.objects.filter(visible=False).order_by('timestamp').first()
        self.assertEqual(self.client.get(f'/transactions/{future.pk}/').status_code, 404)
        self.assertNotContains(self.client.get('/export/'), future.pk)
        self.assertNotContains(self.client.get(f'/accounts/{future.sender_id}/'), future.pk)
        self.assertFalse(tick())
        self.client.post('/monitor/playback/', {'action': 'running'})
        self.assertTrue(tick())
        self.assertFalse(tick(timezone.now() + timedelta(seconds=5)))  # Queue backpressure.
        self.assertEqual(Transaction.objects.filter(visible=True).count(), HISTORY + 1)
        self.assertTrue(process_next())
        future.refresh_from_db()
        self.assertIsNotNone(future.risk)
        # Full replay and incremental scoring must use identical causal evidence and policy.
        original = future.assessments.get()
        replay = analyze(origin=ORIGIN)
        later = future.assessments.get(run=replay)
        self.assertEqual((original.forest, original.lof, original.cluster, original.risk),
                         (later.forest, later.lof, later.cluster, later.risk))
        self.assertTrue(tick(timezone.now() + timedelta(seconds=6)))

    def test_rescoring_updates_explanation_without_overwriting_investigation(self):
        tx = Transaction.objects.filter(visible=True, risk__isnull=False).first()
        original = (tx.risk, tx.decision)
        case = FraudCase.objects.filter(transaction=tx).first()
        if case:
            case.notes.create(text='Notă păstrată la recalculare')
        Transaction.objects.filter(pk=tx.pk).update(risk_explanation={})
        replay = analyze(origin=ORIGIN)
        tx.refresh_from_db()
        self.assertEqual((tx.risk,tx.decision), original)
        self.assertEqual(tx.display_risk,tx.assessments.get(run=replay).risk)
        self.assertEqual(tx.risk_explanation,tx.assessments.get(run=replay).explanation)
        page = self.client.get(f'/transactions/{tx.pk}/')
        self.assertContains(page,'Toți factorii și contribuțiile')
        self.assertContains(page,'Elemente favorabile')
        account = self.client.get(f'/accounts/{tx.sender_id}/')
        self.assertContains(account,'Ultimul transfer evaluat')
        self.assertContains(account,'De ce acest risc?')
        if case: self.assertEqual(case.notes.get().text,'Notă păstrată la recalculare')

    def test_client_uses_latest_current_score_instead_of_lifetime_maximum(self):
        tx = Transaction.objects.filter(visible=True,risk__isnull=False).order_by('-timestamp').first()
        sender = tx.sender
        sender.risk = 100
        sender.save()
        info = {**tx.risk_explanation,'score':7,'level':'Scăzut','style':'allow'}
        Transaction.objects.filter(pk=tx.pk).update(risk=100,risk_explanation=info)
        page = self.client.get('/accounts/',{'q':sender.pk})
        self.assertContains(page,'7 / 100')
        self.assertNotContains(page,'100 / 100')
        profile = self.client.get(f'/accounts/{sender.pk}/')
        self.assertEqual(profile.context['latest_tx'].pk,tx.pk)
        self.assertEqual(profile.context['risk_info']['score'],7)

    def test_metric_export_separates_original_test_and_playback_history(self):
        data = self.client.get('/export/?kind=metrics').json()
        self.assertEqual(data['historical_test']['test_rows'],768)
        self.assertIn(ORIGIN,data['latest_visible_replay'])

    def test_controls_require_auth_post_and_resume_survives_restart(self):
        self.assertEqual(self.client.get('/monitor/playback/').status_code, 405)
        self.assertEqual(self.client.post('/monitor/playback/', {'action': 'bad'}).status_code, 400)
        self.client.post('/monitor/playback/', {'action': 'running'})
        self.assertTrue(tick())
        process_next()
        self.client.post('/monitor/playback/', {'action': 'paused'})
        self.assertFalse(tick(timezone.now()+timedelta(seconds=10)))
        self.assertEqual(DemoPlayback.objects.get(pk=1).released, 1)
        self.client.logout()
        for path in ('/monitor/dashboard/', '/metrics/', '/monitor/playback/'):
            self.assertEqual(self.client.post(path, {'action':'running'}).status_code, 302)

    def test_dashboard_and_analyst_pages_hide_model_diagnostics(self):
        tx = Transaction.objects.filter(visible=True, risk__gte=60).first()
        for path in ('/', '/algorithms/', f'/transactions/{tx.pk}/'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            for name in ('Isolation Forest','DBSCAN','LOF','Local Outlier Factor'):
                self.assertNotContains(response,name)
        data = self.client.get('/monitor/dashboard/?hours=1').json()
        self.assertIn('Activitatea transferurilor', data['html'])
        self.assertIn('secflow_worker_up 0',self.client.get('/metrics/').content.decode())
        tick()
        self.assertIn('secflow_worker_up 1',self.client.get('/metrics/').content.decode())

    def test_repeat_appends_stream_and_preserves_case_notes_and_history(self):
        self.assertFalse(repeat_stream())
        case = FraudCase.objects.first()
        case.notes.create(text='Investigație păstrată')
        Transaction.objects.filter(visible=False).update(visible=True)
        state = DemoPlayback.objects.get(pk=1)
        state.status = 'completed'
        state.save()
        previous_max = Transaction.objects.order_by('-timestamp').first().timestamp
        self.assertTrue(repeat_stream())
        self.assertEqual(Transaction.objects.filter(visible=False).count(), 240)
        self.assertGreater(Transaction.objects.filter(visible=False).order_by('timestamp').first().timestamp, previous_max)
        self.assertEqual(case.notes.get().text, 'Investigație păstrată')
        self.assertTrue(tick())
        process_next()
        self.assertEqual(AnalysisJob.objects.get().status, 'completed')
