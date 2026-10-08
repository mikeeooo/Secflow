from django.test import TestCase
from django.contrib.auth.models import User
from core.models import Account, Transaction, FraudCase, AuditEvent, DetectionRun
class WorkflowTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('analyst',password='test')
        self.admin=User.objects.create_superuser('admin',password='test')
        self.a=Account.objects.create(id='A',blocked=True)
        self.b=Account.objects.create(id='B')
        self.tx=Transaction.objects.create(id='T',sender=self.a,recipient=self.b,amount=100,timestamp=1,kind='TRANSFER',origin='Generated scenario',currency='MDL',device='D',risk=80,decision='Block')
        self.case=FraudCase.objects.create(transaction=self.tx)
    def test_authentication_required(self):
        self.assertEqual(self.client.get('/').status_code,302)
    def test_pages_render_and_export(self):
        self.client.force_login(self.user)
        for url in ['/','/transactions/','/transactions/?q=T','/transactions/?q=A&decision=Block','/transactions/T/','/cases/',f'/cases/{self.case.pk}/','/accounts/','/accounts/A/','/algorithms/','/audit/','/export/','/export/?kind=metrics']:
            self.assertEqual(self.client.get(url).status_code,200,url)
    def test_analyst_cannot_run_or_import(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post('/analysis/run/').status_code,302)
        self.assertEqual(self.client.post('/data/import/').status_code,302)
        self.assertFalse(DetectionRun.objects.exists())
    def test_unblock_requires_reason_and_preserves_transfer(self):
        self.client.force_login(self.user)
        self.client.post('/accounts/A/',{'action':'unblock','reason':''})
        self.a.refresh_from_db(); self.assertTrue(self.a.blocked)
        self.client.post('/accounts/A/',{'action':'unblock','reason':'Identity verified'})
        self.a.refresh_from_db(); self.tx.refresh_from_db()
        self.assertFalse(self.a.blocked); self.assertEqual(self.tx.decision,'Block')
        self.assertEqual(AuditEvent.objects.get().reason,'Identity verified')
    def test_resolve_case_requires_outcome_and_note(self):
        self.client.force_login(self.user)
        url=f'/cases/{self.case.pk}/'
        self.client.post(url,{'status':'Resolved','note':'Checked'})
        self.case.refresh_from_db(); self.assertEqual(self.case.status,'Open')
        self.client.post(url,{'status':'Resolved','note':'Checked','outcome':'False positive'})
        self.case.refresh_from_db(); self.assertEqual(self.case.status,'Resolved')
        self.assertEqual(self.case.notes.count(),1)
        self.assertContains(self.client.get(url), 'selected>False positive')
        response=self.client.post(url,{'status':'Resolved','note':'Unsaved findings'})
        self.assertContains(response,'Unsaved findings')
    def test_csrf_enforced(self):
        from django.test import Client
        client=Client(enforce_csrf_checks=True); client.force_login(self.user)
        self.assertEqual(client.post('/accounts/A/',{'action':'unblock','reason':'test'}).status_code,403)

class ReplayTests(TestCase):
    def test_rerun_preserves_corrections_and_labels_do_not_affect_scores(self):
        from core.services import analyze
        from core.models import Assessment
        user=User.objects.create_user('reviewer')
        a=Account.objects.create(id='SIM_A'); b=Account.objects.create(id='SIM_B')
        Transaction.objects.bulk_create([Transaction(id=f'SIM_{i:04}',sender=a,recipient=b,amount=100+i%5,timestamp=i*400,kind='TRANSFER',origin='Generated scenario',currency='DEMO_UNIT',device='D',truth=False) for i in range(205)])
        run1=analyze(user,trees=8)
        original=list(Assessment.objects.filter(run=run1).order_by('transaction_id').values_list('forest','lof','risk'))
        Transaction.objects.update(truth=True)
        a.blocked=False; a.save()
        tx=Transaction.objects.get(pk='SIM_0204'); tx.decision='Block'; tx.save()
        run2=analyze(user,trees=8)
        repeated=list(Assessment.objects.filter(run=run2).order_by('transaction_id').values_list('forest','lof','risk'))
        self.assertEqual(original,repeated)
        tx.refresh_from_db(); a.refresh_from_db()
        self.assertEqual(tx.decision,'Block'); self.assertFalse(a.blocked)
        self.assertEqual(run2.count,77)
    def test_import_idempotent(self):
        import tempfile, csv
        from core.services import import_dataset
        keys=['transaction_id','nameOrig','nameDest','amount','timestamp_seconds','device_id','ground_truth_fraud','currency','data_origin','failed_login_attempts','type']
        with tempfile.NamedTemporaryFile(mode='w+',suffix='.csv') as file:
            writer=csv.DictWriter(file,fieldnames=keys);writer.writeheader()
            writer.writerow(dict(zip(keys,['T','A','B','10','0','D','0','DEMO_UNIT','Generated scenario','0','TRANSFER'])))
            file.flush()
            self.assertEqual(import_dataset(file.name),1)
            self.assertEqual(import_dataset(file.name),0)
            self.assertEqual(Transaction.objects.count(),1)
