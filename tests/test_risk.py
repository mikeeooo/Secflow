from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from datasets.demo_mia import generate, HISTORY
from detection.features import build
from detection.mia import assess, fit
from detection.risk import explain


def portfolio():
    return [SimpleNamespace(sender_id=row['nameOrig'], recipient_id=row['nameDest'],
                            amount=Decimal(row['amount']), timestamp=row['timestamp_seconds'],
                            device=row['device_id'], failed_logins=row['failed_login_attempts'])
            for row in generate()[:HISTORY]]


class RiskTests(SimpleTestCase):
    def setUp(self):
        self.evidence = dict(history_count=10, amount_ratio=1, amount=100, prior_mean=100,
                             recent_count=0, recent_count_60=0, new_device=False,
                             new_beneficiary=False, failed_logins=0, recent_incoming=0)

    def score(self, **changes):
        return explain(.42, 1.1, 0, [.65, 3], {**self.evidence, **changes})

    def test_observable_factors_raise_score_and_explain_it(self):
        baseline = self.score()
        for change, key in [({'amount_ratio':16,'amount':1600},'amount'),
                             ({'recent_count':6,'recent_count_60':3},'frequency'),
                             ({'new_device':True},'device'), ({'failed_logins':6},'access'),
                             ({'new_beneficiary':True},'beneficiary'),
                             ({'recent_incoming':4},'incoming'), ({'history_count':0},'history')]:
            with self.subTest(key=key):
                changed = self.score(**change)
                self.assertGreater(changed['score'],baseline['score'])
                factor = next(f for f in changed['factors'] if f['key'] == key)
                self.assertGreater(factor['points'],0)
                self.assertTrue(factor['detail'])
        self.assertEqual(baseline['level'],'Scăzut')
        self.assertTrue(any(f['key']=='device' for f in baseline['supportive']))

    def test_exact_additive_total_limits_and_no_random_jitter(self):
        result = self.score(amount_ratio=7,failed_logins=4,new_device=True,recent_count=3)
        self.assertEqual(result,self.score(amount_ratio=7,failed_logins=4,new_device=True,recent_count=3))
        self.assertEqual(sum(f['maximum'] for f in result['factors']),100)
        self.assertEqual(round(sum(f['points'] for f in result['factors'])),result['score'])
        self.assertAlmostEqual(result['total_points']+result['rounding'], result['score'])
        for forest,lof,cluster in [(0,1,0),(1,999999,-1)]:
            value = explain(forest,lof,cluster,[.65,3],self.evidence)
            self.assertTrue(0 <= value['score'] <= 100)

    def test_dataset_has_gradual_scores_without_label_or_scenario_features(self):
        features = build(portfolio())
        labels = [bool(row['ground_truth_fraud']) for row in generate()[:HISTORY]]
        model, vectors, config = fit(features, labels)
        results = [assess(model, vectors[i], features[i][1], vectors[max(0,i-23):i+1], config['thresholds'])
                   for i in range(512,HISTORY)]
        self.assertGreaterEqual(len(set(r['risk'] for r in results)),30)
        altered = {**features[-1][1], 'truth':True, 'scenario_type':'fraud'}
        first = assess(model,vectors[-1],features[-1][1],vectors[-24:],config['thresholds'])
        second = assess(model,vectors[-1],altered,vectors[-24:],config['thresholds'])
        self.assertEqual(first,second)
        self.assertTrue(all(r['risk']==r['explanation']['score'] for r in results))

    def test_evidence_uses_only_prior_history(self):
        rows = [SimpleNamespace(sender_id='A',recipient_id='B',amount=100,timestamp=0,device='D',failed_logins=0),
                SimpleNamespace(sender_id='A',recipient_id='B',amount=200,timestamp=30,device='D',failed_logins=2)]
        evidence = build(rows)[1][1]
        self.assertEqual(evidence['prior_mean'],100)
        self.assertEqual(evidence['amount_ratio'],2)
        self.assertEqual(evidence['recent_count_60'],1)
        self.assertFalse(evidence['new_beneficiary'])
        self.assertFalse(evidence['new_device'])
