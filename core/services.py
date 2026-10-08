import csv, hashlib, json, time
from pathlib import Path
from django.db import transaction as atomic
from core.models import Account, Transaction, DatasetImport, DetectionRun, Assessment, FraudCase, AuditEvent
from detection.features import build, Scaler, NAMES
from detection.algorithms import IsolationForest, LocalOutlierFactor, DBSCAN
from detection.evaluation import metrics

@atomic.atomic
def import_dataset(path, paysim_limit=2000):
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw + str(paysim_limit).encode()).hexdigest()
    if DatasetImport.objects.filter(checksum=digest).exists(): return 0
    required = {'transaction_id','nameOrig','nameDest','amount','timestamp_seconds','device_id','ground_truth_fraud','currency','data_origin','failed_login_attempts','type'}
    rows, seen, paysim = [], set(), 0
    reader = csv.DictReader(raw.decode().splitlines())
    if not required.issubset(reader.fieldnames or []): raise ValueError('Dataset schema is missing required columns.')
    from decimal import Decimal, InvalidOperation
    for r in reader:
        if r['data_origin'] == 'PaySim':
            paysim += 1
            if paysim_limit and paysim > paysim_limit: continue
        if r['transaction_id'] in seen: raise ValueError('Duplicate transaction ID in input.')
        seen.add(r['transaction_id'])
        amount = Decimal(r['amount'])
        if not amount.is_finite() or amount < 0 or int(r['timestamp_seconds']) < 0 or int(r['failed_login_attempts']) < 0: raise ValueError('Invalid transaction value.')
        if not r['nameOrig'] or not r['nameDest'] or r['ground_truth_fraud'] not in ('0','1'): raise ValueError('Invalid identity or label.')
        rows.append(r)
    Account.objects.bulk_create([Account(id=i) for i in {r[k] for r in rows for k in ('nameOrig','nameDest')}],ignore_conflicts=True)
    Transaction.objects.bulk_create([Transaction(id=r['transaction_id'],sender_id=r['nameOrig'],recipient_id=r['nameDest'],amount=r['amount'],timestamp=int(r['timestamp_seconds']),kind=r['type'],origin=r['data_origin'],currency=r['currency'],device=r['device_id'],failed_logins=int(r['failed_login_attempts']),truth=r['ground_truth_fraud']=='1',metadata=r) for r in rows],ignore_conflicts=True)
    DatasetImport.objects.create(checksum=digest,name=Path(path).name,rows=len(rows))
    return len(rows)

def rules(e):
    reasons, score = [],0
    for condition,weight,label in [(e['history_count']>=5 and e['amount_ratio']>8,40,'Amount exceeds eight times prior account mean'),(e['recent_count']>=8,30,'At least eight prior transfers within five minutes'),(e['failed_logins']>=3 and e['new_device'],50,'New device after repeated failed sign-ins'),(e['recent_incoming']>=3,25,'Rapid outgoing activity after multiple incoming transfers')]:
        if condition: reasons.append(label); score += weight
    return min(score,100),reasons

@atomic.atomic
def analyze(actor=None, trees=32, eps=1.8, k=10):
    if not 8 <= trees <= 100 or not .1 <= eps <= 10 or not 2 <= k <= 30: raise ValueError('Parameters outside allowed ranges.')
    start = time.perf_counter()
    run = DetectionRun.objects.create(actor=actor,parameters={'trees':trees,'sample_size':64,'seed':42,'eps':eps,'min_samples':4,'k':k,'reference':128,'validation':64,'dbscan_window':24,'features':NAMES,'mode':'Chronological replay; fixed earlier reference, causal DBSCAN window','score':'0.30 IF + 0.25 LOF + 0.15 DBSCAN noise + 0.30 rules; review >=45, block >=65','calibration':'Not calibrated; fixed demonstrator thresholds','datasets':list(DatasetImport.objects.values('checksum','rows'))})
    results, count = {},0
    for origin in Transaction.objects.order_by().values_list('origin',flat=True).distinct():
        rows = list(Transaction.objects.filter(origin=origin).order_by('timestamp','id'))
        if len(rows)<200: raise ValueError('Each source needs at least 200 transactions for chronological reference, validation and test.')
        features = build(rows)
        scaler = Scaler().fit([v for v,_ in features[:128]])
        vectors = [scaler.transform(v) for v,_ in features]
        fit_start = time.perf_counter()
        forest = IsolationForest(trees,64,42).fit(vectors[:128])
        lof = LocalOutlierFactor(k).fit(vectors[:128])
        fit_seconds = time.perf_counter()-fit_start
        assessments, eval_rows = [],[]
        for i,(tx,(v,e),point) in enumerate(zip(rows,features,vectors)):
            tx.features,tx.evidence=v,e
            if i<128: continue
            fs,ls = forest.score(point),lof.score(point)
            cluster = DBSCAN(eps,4).fit_predict(vectors[max(0,i-23):i+1])[-1]
            rs,reasons=rules(e)
            fscore=max(0,min(100,(fs-.35)/.4*100)); lscore=max(0,min(100,(ls-1)*50))
            risk=round(.30*fscore+.25*lscore+.15*(100 if cluster==-1 else 0)+.30*rs)
            if fs >= .6: reasons.append('Isolation Forest: short isolation path')
            if ls >= 1.5: reasons.append('LOF: lower density than reference neighbors')
            if cluster == -1: reasons.append('DBSCAN: noise in trailing 24-transfer window')
            if e['history_count']<5: reasons.append('Limited prior account history')
            decision = 'Block' if risk>=65 else 'Review' if risk>=45 else 'Allow'
            # Preserve operational decisions and manual account corrections on reruns.
            initial = tx.decision == 'Pending'
            if initial:
                if Account.objects.filter(pk=tx.sender_id,blocked=True).exists(): decision='Block'; reasons.append('Sender already restricted in simulation')
                tx.risk,tx.decision=risk,decision
                if decision=='Block':
                    changed=Account.objects.filter(pk=tx.sender_id,blocked=False).update(blocked=True)
                    if changed: AuditEvent.objects.create(actor=actor,action='Automatic account restriction',target=tx.sender_id,reason=f'Transfer {tx.pk}: risk {risk}',before='Active',after='Blocked')
                if decision!='Allow': FraudCase.objects.get_or_create(transaction=tx)
                Account.objects.filter(pk=tx.sender_id,risk__lt=risk).update(risk=risk)
            split='validation' if i<192 else 'test'
            assessments.append(Assessment(transaction=tx,run=run,forest=fs,lof=ls,cluster=cluster,risk=risk,decision=decision,reasons=reasons,split=split))
            eval_rows.append((tx.truth,fs>=.6,ls>=1.5,cluster==-1,rs>=40,(fscore*.43+lscore*.36+(100 if cluster==-1 else 0)*.21)>=45,risk>=45,split))
        Transaction.objects.bulk_update(rows,['features','evidence','risk','decision'],batch_size=400)
        Assessment.objects.bulk_create(assessments,batch_size=400)
        results[origin]={'fit_seconds':round(fit_seconds,4),'reference_rows':128,'validation_rows':64,'test_rows':len(rows)-192,'methods':{}}
        for split in ('validation','test'):
            selected=[r for r in eval_rows if r[-1]==split and r[0] is not None]
            results[origin]['methods'][split]={name:metrics([r[0] for r in selected],[r[j] for r in selected]) for j,name in enumerate(['Isolation Forest','LOF','DBSCAN noise','Rules','Algorithms only','Combined'],1)}
        count+=len(assessments)
    run.metrics,run.duration,run.count=results,time.perf_counter()-start,count
    run.save()
    AuditEvent.objects.create(actor=actor,action='Analysis completed',target=str(run.pk),reason='Chronological replay',after=str(count))
    return run
