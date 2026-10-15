"""Presentation policy. Fit on reference, choose thresholds on validation only."""
from .pipeline import DetectionModel, parameters, WINDOW_SIZE
from .evaluation import metrics
from .risk import explain, VERSION, REVIEW, BLOCK

ORIGIN = 'MIA demo'
REFERENCE = 256
VALIDATION = 256
CANDIDATES = ((.5, .55, .6, .65, .7, .75), (1.3, 1.5, 2, 3, 5, 10))


def fit(features, labels=None, thresholds=None):
    config = {**parameters(48), 'reference': REFERENCE, 'validation': VALIDATION,
              'score': '55 continuous model points + 45 observable behavior points',
              'policy_version': VERSION, 'review_threshold': REVIEW, 'block_threshold': BLOCK}
    model = DetectionModel([vector for vector, _ in features[:REFERENCE]], config)
    vectors = [model.scaler.transform(vector) for vector, _ in features]
    if thresholds is None:
        if len(features) < REFERENCE + VALIDATION or labels is None:
            raise ValueError('Portofoliul MIA necesită 256 de exemple de referință și 256 de validare.')
        validation = []
        for index in range(REFERENCE, REFERENCE + VALIDATION):
            validation.append(model.scores(vectors[index], vectors[max(0, index-WINDOW_SIZE+1):index+1])[:2])
        truth = labels[REFERENCE:REFERENCE + VALIDATION]
        thresholds = [max(grid, key=lambda threshold: (
            metrics(truth, [row[column] >= threshold for row in validation])['f1'], threshold))
            for column, grid in enumerate(CANDIDATES)]
    config['thresholds'] = thresholds
    config['calibration'] = 'F1 on chronological validation only; held-out test never selects thresholds'
    return model, vectors, config


def assess(model, point, evidence, window, thresholds):
    raw_forest, raw_lof, cluster = model.scores(point, window)
    result = {'forest': raw_forest, 'lof': raw_lof, 'cluster': cluster}
    forest, lof, noise = result['forest'] >= thresholds[0], result['lof'] >= thresholds[1], result['cluster'] == -1
    explanation = explain(raw_forest, raw_lof, cluster, thresholds, evidence)
    risk = explanation['score']
    reasons = [factor['detail'] for factor in explanation['drivers']]
    result.update(risk=risk, decision='Block' if risk >= BLOCK else 'Review' if risk >= REVIEW else 'Allow',
                  explanation=explanation, reasons=reasons,
                  predictions=[forest, lof, noise, False, risk >= REVIEW, risk >= REVIEW])
    return result
