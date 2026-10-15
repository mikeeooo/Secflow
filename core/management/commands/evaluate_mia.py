"""Reproduce the original historical test, independently of local playback state."""
import json
from types import SimpleNamespace

from django.conf import settings
from django.core.management.base import BaseCommand

from datasets.demo_mia import generate, HISTORY, SEED
from detection.evaluation import metrics
from detection.features import build
from detection.mia import assess, fit, REFERENCE, VALIDATION


class Command(BaseCommand):
    help = 'Evaluează politica actuală pe testul istoric sintetic; nu modifică baza de date.'

    def handle(self, *args, **options):
        rows = generate()[:HISTORY]
        requests = [SimpleNamespace(sender_id=row['nameOrig'],recipient_id=row['nameDest'],
                                   amount=float(row['amount']),timestamp=row['timestamp_seconds'],
                                   device=row['device_id'],failed_logins=row['failed_login_attempts']) for row in rows]
        features = build(requests)
        truth = [bool(row['ground_truth_fraud']) for row in rows]
        model, vectors, config = fit(features, truth)
        predictions = [assess(model, vectors[i], features[i][1], vectors[max(0,i-23):i+1], config['thresholds'])
                       for i in range(REFERENCE+VALIDATION,HISTORY)]
        labels = truth[REFERENCE+VALIDATION:]
        report = {'source': 'Entirely synthetic MIA portfolio; original historical test only',
                  'dataset_seed': SEED, 'parameters': config,
                  'reference_rows': REFERENCE, 'validation_rows': VALIDATION, 'test_rows':len(predictions),
                  'score_values': sorted({result['risk'] for result in predictions}),
                  'methods': {name: metrics(labels,[result['predictions'][column] for result in predictions])
                              for column,name in [(0,'Isolation Forest'),(1,'LOF'),(2,'DBSCAN noise'),(5,'Combined')]}}
        path = settings.BASE_DIR/'artifacts/mia-continuous-evaluation.json'
        path.write_text(json.dumps(report,indent=2)+'\n')
        self.stdout.write(json.dumps({'scores':len(report['score_values']), 'test':report['methods']['Combined']},indent=2))
