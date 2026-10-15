"""Database workflows. The numerical work lives in detection/pipeline.py."""
import csv
import hashlib
import io
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.db import transaction
from django.db.models import Q

from core.models import Account, Assessment, AuditEvent, DatasetImport, DetectionRun, FraudCase, Transaction
from detection import mia
from detection.evaluation import metrics
from detection.features import build
from detection.pipeline import DetectionModel, REFERENCE_SIZE, VALIDATION_SIZE, WINDOW_SIZE, parameters


@transaction.atomic
def import_dataset(path, paysim_limit=2000):
    """Validate the selected CSV completely before inserting anything."""
    if paysim_limit < 0:
        raise ValueError('Limita PaySim trebuie să fie zero (toate rândurile) sau un număr pozitiv.')
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw + str(paysim_limit).encode()).hexdigest()
    if DatasetImport.objects.filter(checksum=digest).exists():
        return 0
    required = {'transaction_id', 'nameOrig', 'nameDest', 'amount', 'timestamp_seconds',
                'device_id', 'ground_truth_fraud', 'currency', 'data_origin',
                'failed_login_attempts', 'type'}
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('Lipsesc coloane obligatorii din setul de date.')
    rows, seen, paysim = [], set(), 0
    for line, row in enumerate(reader, 2):
        if row['data_origin'] == 'PaySim':
            paysim += 1
            if paysim_limit and paysim > paysim_limit:
                continue
        try:
            if any(row[key] is None or not row[key].strip() for key in required):
                raise ValueError('Câmpurile obligatorii nu pot fi goale.')
            for key in ('transaction_id', 'nameOrig', 'nameDest', 'device_id'):
                if len(row[key]) > 80:
                    raise ValueError(f'Câmpul {key} depășește 80 de caractere.')
            if row['transaction_id'] in seen:
                raise ValueError('ID de tranzacție duplicat în fișier.')
            amount = Decimal(row['amount'])
            if not amount.is_finite() or not 0 <= amount < Decimal('1e16') or amount != amount.quantize(Decimal('.01')):
                raise ValueError('Suma trebuie să fie finită, nenegativă și să aibă cel mult două zecimale.')
            if not 0 <= int(row['timestamp_seconds']) < 2**63 or not 0 <= int(row['failed_login_attempts']) <= 1000000:
                raise ValueError('Timpul sau numărul autentificărilor eșuate este în afara intervalului permis.')
            if row['ground_truth_fraud'] not in ('0', '1'):
                raise ValueError('Eticheta de fraudă trebuie să fie 0 sau 1.')
            units = {'PaySim': 'PAYSIM_UNIT', 'Generated scenario': 'DEMO_UNIT', mia.ORIGIN: 'MDL'}
            if units.get(row['data_origin']) != row['currency']:
                raise ValueError('Sursa și unitatea monetară nu corespund convenției setului de date.')
            if len(row['type']) > 30:
                raise ValueError('Tipul tranzacției depășește 30 de caractere.')
        except (ValueError, InvalidOperation) as error:
            raise ValueError(f'Rândul CSV {line}: {error}') from error
        seen.add(row['transaction_id'])
        rows.append(row)
    if not rows:
        raise ValueError('Setul de date nu conține tranzacții selectate.')
    account_ids = {row[key] for row in rows for key in ('nameOrig', 'nameDest')}
    from .demo import fictional_name
    Account.objects.bulk_create([Account(id=key, display_name=fictional_name(key)) for key in sorted(account_ids)], ignore_conflicts=True)
    Transaction.objects.bulk_create([
        Transaction(id=row['transaction_id'], sender_id=row['nameOrig'], recipient_id=row['nameDest'],
                    amount=row['amount'], timestamp=int(row['timestamp_seconds']), kind=row['type'],
                    origin=row['data_origin'], currency=row['currency'], device=row['device_id'],
                    failed_logins=int(row['failed_login_attempts']), truth=row['ground_truth_fraud'] == '1',
                    metadata=row, visible=row.get('phase') != 'stream')
        for row in rows
    ], ignore_conflicts=True, batch_size=400)
    DatasetImport.objects.create(checksum=digest, name=Path(path).name, rows=len(rows))
    return len(rows)


def record_assessment(tx, result, run, split, accounts, cases, events):
    """Keep the first operational decision; append every later assessment."""
    tx.risk_explanation = result.get('explanation', {})
    was_pending = tx.decision == 'Pending'
    if was_pending:
        sender = accounts[tx.sender_id]
        if sender.blocked:
            result['decision'] = 'Block'
            result['reasons'].append('Sender already restricted in simulation')
        tx.risk, tx.decision = result['risk'], result['decision']
        sender.risk = max(sender.risk, tx.risk)
        if tx.decision == 'Block' and not sender.blocked and tx.origin != mia.ORIGIN:
            sender.blocked = True
            events.append(AuditEvent(actor=run.actor, action='Automatic account restriction',
                                     target=sender.pk, reason=f'Transfer {tx.pk}: risk {tx.risk}',
                                     before='Active', after='Blocked'))
        if tx.decision != 'Allow':
            cases.append(FraudCase(transaction=tx))
    if not was_pending and tx.origin == mia.ORIGIN and result['risk'] >= mia.REVIEW:
        cases.append(FraudCase(transaction=tx))
    return Assessment(transaction=tx, run=run, split=split, explanation=tx.risk_explanation,
                      **{key: result[key] for key in ('forest', 'lof', 'cluster', 'risk', 'decision', 'reasons')})


@transaction.atomic
def analyze(actor=None, trees=32, eps=1.8, k=10, origin=None):
    """Replay each source separately; fit once and write results in batches."""
    config = parameters(trees, eps, k)
    start = time.perf_counter()
    run = DetectionRun.objects.create(actor=actor, parameters={
        **config, 'mode': 'replay', 'datasets': list(DatasetImport.objects.values('checksum', 'rows')),
    })
    accounts = Account.objects.in_bulk()
    results, all_cases, events, count = {}, [], [], 0
    source_rows = Transaction.objects.filter(visible=True)
    if origin:
        source_rows = source_rows.filter(origin=origin)
    origins = source_rows.order_by('origin').values_list('origin', flat=True).distinct()
    for origin in origins:
        rows = list(source_rows.filter(origin=origin).order_by('timestamp', 'id'))
        if len(rows) < 200:
            raise ValueError(f'{origin}: importă cel puțin 200 de tranzacții înainte de analiză.')
        features = build(rows)
        reference, validation = REFERENCE_SIZE, VALIDATION_SIZE
        source_config = config
        if origin == mia.ORIGIN:
            model, vectors, source_config = mia.fit(features, [tx.truth for tx in rows])
            reference, validation = mia.REFERENCE, mia.VALIDATION
            run.parameters['mia'] = source_config
        else:
            model = DetectionModel([vector for vector, _ in features[:reference]], config)
            vectors = [model.scaler.transform(vector) for vector, _ in features]
        assessments, evaluation = [], []
        for index, (tx, (vector, evidence)) in enumerate(zip(rows, features)):
            tx.features, tx.evidence = vector, evidence
            if index < reference:
                continue
            window = vectors[max(0, index - WINDOW_SIZE + 1):index + 1]
            result = (mia.assess(model, vectors[index], evidence, window, source_config['thresholds'])
                      if origin == mia.ORIGIN else model.assess(vectors[index], evidence, window))
            split = 'validation' if index < reference + validation else 'test'
            # Evaluation measures algorithm predictions, independently of account restrictions.
            if tx.truth is not None:
                evaluation.append((tx.truth, result['predictions'], split))
            assessments.append(record_assessment(tx, result, run, split, accounts, all_cases, events))
        Transaction.objects.bulk_update(rows, ['features', 'evidence', 'risk', 'decision', 'risk_explanation'], batch_size=400)
        Assessment.objects.bulk_create(assessments, batch_size=400)
        methods = {}
        names = ['Isolation Forest', 'LOF', 'DBSCAN noise', 'Rules', 'Algorithms only', 'Combined']
        for split in ('validation', 'test'):
            selected = [row for row in evaluation if row[2] == split]
            methods[split] = {name: metrics([row[0] for row in selected], [row[1][i] for row in selected])
                              for i, name in enumerate(names)
                              if origin != mia.ORIGIN or name in ('Isolation Forest', 'LOF', 'DBSCAN noise', 'Combined')}
        results[origin] = {
            'fit_seconds': round(model.fit_seconds, 4), 'reference_rows': reference,
            'validation_rows': validation, 'test_rows': len(rows) - reference - validation,
            'methods': methods,
        }
        count += len(assessments)
    if not results:
        raise ValueError('Importă setul de date înainte de analiză.')
    Account.objects.bulk_update(list(accounts.values()), ['risk', 'blocked'], batch_size=400)
    FraudCase.objects.bulk_create(all_cases, ignore_conflicts=True, batch_size=400)
    AuditEvent.objects.bulk_create(events, batch_size=400)
    run.metrics, run.duration, run.count = results, time.perf_counter() - start, count
    run.save()
    AuditEvent.objects.create(actor=actor, action='Analysis completed', target=str(run.pk),
                              reason='Replay cronologic; deciziile existente au fost păstrate', after=str(count))
    return run


@transaction.atomic
def assess_transfer(tx, actor=None):
    """Evaluate only this new transfer, using the same reference and scoring code."""
    start = time.perf_counter()
    rows = list(Transaction.objects.filter(origin=tx.origin, visible=True).filter(
        Q(timestamp__lt=tx.timestamp) | Q(timestamp=tx.timestamp, id__lte=tx.pk)
    ).order_by('timestamp', 'id'))
    if len(rows) < 201 or rows[-1].pk != tx.pk:
        raise ValueError('Simularea necesită cel puțin 200 de tranzacții anterioare și o cerere nouă la finalul istoricului.')
    previous = DetectionRun.objects.exclude(parameters__mode='single').order_by('-pk').first()
    saved = previous.parameters if previous else {}
    config = parameters(saved.get('trees', 32), saved.get('eps', 1.8), saved.get('k', 10))
    features = build(rows)
    if tx.origin == mia.ORIGIN:
        model, vectors, config = mia.fit(features, [row.truth for row in rows],
                                         thresholds=saved.get('mia', {}).get('thresholds'))
        window = vectors[-WINDOW_SIZE:]
    else:
        model = DetectionModel([vector for vector, _ in features[:REFERENCE_SIZE]], config)
        window = [model.scaler.transform(vector) for vector, _ in features[-WINDOW_SIZE:]]
    tx.features, tx.evidence = features[-1]
    result = (mia.assess(model, window[-1], tx.evidence, window, config['thresholds'])
              if tx.origin == mia.ORIGIN else model.assess(window[-1], tx.evidence, window))
    run = DetectionRun.objects.create(actor=actor, parameters={**config, 'mode': 'single', 'source': tx.origin}, count=1)
    accounts = {tx.sender_id: Account.objects.get(pk=tx.sender_id)}
    cases, events = [], []
    assessment = record_assessment(tx, result, run, 'manual', accounts, cases, events)
    tx.save(update_fields=['features', 'evidence', 'risk', 'decision', 'risk_explanation'])
    accounts[tx.sender_id].save(update_fields=['risk', 'blocked'])
    assessment.save()
    FraudCase.objects.bulk_create(cases, ignore_conflicts=True)
    AuditEvent.objects.bulk_create(events)
    run.duration = time.perf_counter() - start
    run.save(update_fields=['duration'])
    return assessment
