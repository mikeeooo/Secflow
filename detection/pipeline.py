"""The complete scoring policy, in plain Python. No database or web imports."""
import time

from .algorithms import DBSCAN, IsolationForest, LocalOutlierFactor
from .features import NAMES, Scaler

REFERENCE_SIZE = 128
VALIDATION_SIZE = 64
WINDOW_SIZE = 24


def parameters(trees=32, eps=1.8, k=10):
    if not 8 <= trees <= 100 or not .1 <= eps <= 10 or not 2 <= k <= 30:
        raise ValueError('Folosește 8–100 de arbori, raza 0,1–10 și 2–30 de vecini.')
    return {
        'trees': trees, 'sample_size': 64, 'seed': 42,
        'eps': eps, 'min_samples': 4, 'k': k,
        'reference': REFERENCE_SIZE, 'validation': VALIDATION_SIZE,
        'dbscan_window': WINDOW_SIZE, 'features': NAMES,
        'score': '0.30 IF + 0.25 LOF + 0.15 DBSCAN noise + 0.30 rules',
        'review_threshold': 45, 'block_threshold': 65,
        'calibration': 'Fixed demonstration thresholds; not a fraud probability',
    }


def rules(evidence):
    """Four observable indicators. Labels never participate in scoring."""
    checks = [
        (evidence['history_count'] >= 5 and evidence['amount_ratio'] > 8,
         40, 'Amount exceeds eight times prior account mean'),
        (evidence['recent_count'] >= 8,
         30, 'At least eight prior transfers within five minutes'),
        (evidence['failed_logins'] >= 3 and evidence['new_device'],
         50, 'New device after repeated failed sign-ins'),
        (evidence['recent_incoming'] >= 3,
         25, 'Rapid outgoing activity after multiple incoming transfers'),
    ]
    return (min(100, sum(weight for triggered, weight, _ in checks if triggered)),
            [reason for triggered, _, reason in checks if triggered])


def contributions(forest, lof, cluster, rule_score):
    """Normalize raw outputs, then show exactly how many points each adds."""
    forest_score = max(0, min(100, (forest - .35) / .4 * 100))
    lof_score = max(0, min(100, (lof - 1) * 50))
    noise_score = 100 if cluster == -1 else 0
    return [
        {'name': 'Isolation Forest', 'weight': 30, 'score': forest_score, 'points': .30 * forest_score},
        {'name': 'Local Outlier Factor', 'weight': 25, 'score': lof_score, 'points': .25 * lof_score},
        {'name': 'DBSCAN noise', 'weight': 15, 'score': noise_score, 'points': .15 * noise_score},
        {'name': 'Behavior rules', 'weight': 30, 'score': rule_score, 'points': .30 * rule_score},
    ]


class DetectionModel:
    """Fit once on the earlier reference; score later requests with that model."""
    def __init__(self, reference, config):
        started = time.perf_counter()
        self.config = config
        self.scaler = Scaler().fit(reference)
        reference = [self.scaler.transform(point) for point in reference]
        self.forest = IsolationForest(config['trees'], config['sample_size'], config['seed']).fit(reference)
        self.lof = LocalOutlierFactor(config['k']).fit(reference)
        self.dbscan = DBSCAN(config['eps'], config['min_samples'])
        self.fit_seconds = time.perf_counter() - started

    def scores(self, point, window):
        """Run all three methods against an already-scaled request/window."""
        return self.forest.score(point), self.lof.score(point), self.dbscan.fit_predict(window)[-1]

    def assess(self, point, evidence, window):
        """Legacy policy. MIA reuses scores() with its own validation-calibrated policy."""
        forest, lof, cluster = self.scores(point, window)
        rule_score, reasons = rules(evidence)
        parts = contributions(forest, lof, cluster, rule_score)
        risk = round(sum(part['points'] for part in parts))
        if forest >= .6:
            reasons.append('Isolation Forest: short isolation path')
        if lof >= 1.5:
            reasons.append('LOF: lower density than reference neighbors')
        if cluster == -1:
            reasons.append('DBSCAN: noise in trailing 24-transfer window')
        if evidence['history_count'] < 5:
            reasons.append('Limited prior account history')
        return {
            'forest': forest, 'lof': lof, 'cluster': cluster, 'risk': risk,
            'decision': 'Block' if risk >= 65 else 'Review' if risk >= 45 else 'Allow',
            'reasons': reasons,
            'predictions': [forest >= .6, lof >= 1.5, cluster == -1, rule_score >= 40,
                            sum(p['score'] * w for p, w in zip(parts, [.43, .36, .21])) >= 45,
                            risk >= 45],
        }
