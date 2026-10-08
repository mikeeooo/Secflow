"""Original PaySim benchmark, chronological tuning and bounded scaling experiment."""
import csv, json, math, time, tracemalloc
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.conf import settings
from detection.algorithms import IsolationForest, DBSCAN, LocalOutlierFactor
from detection.features import Scaler
from detection.evaluation import metrics
class Command(BaseCommand):
    def handle(self,*args,**kwargs):
        path=next((settings.BASE_DIR/'data/raw').glob('*.csv'))
        points,truth=[],[]
        hourly=defaultdict(int)
        with path.open() as f:
            for i,r in enumerate(csv.DictReader(f)):
                if i>=1200: break
                key=(r['nameOrig'],int(r['step']))
                points.append([math.log1p(float(r['amount'])),hourly[key],int(r['type']=='TRANSFER'),int(r['type']=='CASH_OUT')])
                hourly[key]+=1; truth.append(int(r['isFraud']))
        scaler=Scaler().fit(points[:200]); x=[scaler.transform(p) for p in points]
        forest=IsolationForest(32,64,42).fit(x[:200]); lof=LocalOutlierFactor(10).fit(x[:200])
        scores={'Isolation Forest':[forest.score(p) for p in x[200:]],'LOF':[lof.score(p) for p in x[200:]],'DBSCAN noise':[int(DBSCAN(1.8,4).fit_predict(x[max(0,i-23):i+1])[-1]==-1) for i in range(200,len(x))]}
        output={'dataset':'Original PaySim contiguous first 1200 rows; no simulated metadata or balances','features':['log amount','prior sender requests in same source hour','is transfer','is cash out'],'split':{'reference':200,'validation':200,'test':800},'results':{},'scaling':[]}
        for name,s in scores.items():
            candidates=[.5,.55,.6,.65,.7] if name=='Isolation Forest' else [1.2,1.5,2,3] if name=='LOF' else [1]
            threshold=max(candidates,key=lambda t:metrics(truth[200:400],[v>=t for v in s[:200]])['f1'])
            output['results'][name]={'threshold_selected_on_validation':threshold,'validation':metrics(truth[200:400],[v>=threshold for v in s[:200]]),'test':metrics(truth[400:],[v>=threshold for v in s[200:]])}
        for n in [100,200,400]:
            for name,fn in [('Isolation Forest',lambda p:IsolationForest(32,64,42).fit(p)),('DBSCAN',lambda p:DBSCAN(1.8,4).fit_predict(p)),('LOF',lambda p:LocalOutlierFactor(10).fit(p))]:
                tracemalloc.start(); start=time.perf_counter(); fn(x[:n]); elapsed=time.perf_counter()-start
                _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
                output['scaling'].append({'algorithm':name,'n':n,'dimensions':4,'seconds':round(elapsed,5),'peak_python_bytes':peak})
        target=settings.BASE_DIR/'artifacts/benchmark.json'; target.write_text(json.dumps(output,indent=2))
        self.stdout.write(str(target))
