import csv, json
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction as atomic
from django.db.models import Q, Count, Sum, Max
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .models import *
from .services import analyze, import_dataset
from django.conf import settings

staff = user_passes_test(lambda u:u.is_active and u.is_staff)

def shell(request,template,title,**context):
    return render(request,template,dict(title=title,**context))

@login_required
def dashboard(request):
    transactions=Transaction.objects.all()
    counts={r['decision']:r['n'] for r in transactions.values('decision').annotate(n=Count('id'))}
    buckets=list(transactions.extra(select={'day':'timestamp / 86400'}).values('day').annotate(total=Count('id')).order_by('day'))
    peak=max([r['total'] for r in buckets] or [1])
    for b in buckets: b['height']=round(b['total']/peak*100)
    return shell(request,'dashboard.html','Overview',total=transactions.count(),review=FraudCase.objects.filter(transaction__decision='Review').exclude(status='Resolved').count(),blocked=Account.objects.filter(blocked=True).count(),allowed=counts.get('Allow',0),cases=FraudCase.objects.select_related('transaction').exclude(status='Resolved').order_by('-transaction__risk')[:6],buckets=buckets,run=DetectionRun.objects.last(),impact=list(transactions.exclude(truth=None).values('currency').annotate(blocked_fraud=Sum('amount',filter=Q(truth=True,decision='Block')),allowed_fraud=Sum('amount',filter=Q(truth=True,decision='Allow')),legitimate_blocks=Count('id',filter=Q(truth=False,decision='Block')))),sums=list(transactions.values('currency').annotate(value=Sum('amount'))),origins=list(transactions.values('origin').annotate(n=Count('id'))))

@login_required
def transactions(request):
    qs=Transaction.objects.all()
    q=request.GET.get('q','').strip()
    if q: qs=qs.filter(Q(id__icontains=q)|Q(sender__id__icontains=q)|Q(recipient__id__icontains=q))
    for field in ['decision','origin']:
        if request.GET.get(field): qs=qs.filter(**{field:request.GET[field]})
    return shell(request,'transactions.html','Transactions',page=Paginator(qs,25).get_page(request.GET.get('page')),q=q)

@login_required
def detail(request,pk):
    tx=get_object_or_404(Transaction,pk=pk)
    return shell(request,'detail.html','Transfer details',tx=tx,assessment=tx.assessments.order_by('-run_id').first(),case=FraudCase.objects.filter(transaction=tx).first())

@login_required
def cases(request):
    qs=FraudCase.objects.select_related('transaction','assignee').order_by('-transaction__risk')
    if request.GET.get('status'): qs=qs.filter(status=request.GET['status'])
    return shell(request,'cases.html','Fraud cases',page=Paginator(qs,25).get_page(request.GET.get('page')))

@login_required
def case_detail(request,pk):
    case=get_object_or_404(FraudCase.objects.select_related('transaction'),pk=pk)
    if request.method=='POST':
        status=request.POST.get('status'); outcome=request.POST.get('outcome',''); note=request.POST.get('note','').strip()
        if status not in ['Open','Investigating','Resolved'] or outcome not in ['','Confirmed fraud','False positive','Inconclusive'] or (status=='Resolved' and not outcome) or not note:
            messages.error(request,'Add a note and choose an outcome when resolving a case.')
        else:
            with atomic.atomic():
                before=case.status
                case.status=status; case.outcome=outcome if status=='Resolved' else ''; case.assignee=request.user; case.save()
                CaseNote.objects.create(case=case,author=request.user,text=note)
                AuditEvent.objects.create(actor=request.user,action='Case updated',target=str(case.pk),reason=note,before=before,after=status)
            messages.success(request,'Investigation saved. Transfer and account decisions remain separate.')
            return redirect('case',pk=pk)
    return shell(request,'case.html','Investigation',case=case,selected_status=request.POST.get('status',case.status),selected_outcome=request.POST.get('outcome',case.outcome),draft_note=request.POST.get('note',''),notes=case.notes.select_related('author').order_by('-created'))

@login_required
def accounts(request):
    qs=Account.objects.order_by('-risk','id')
    if request.GET.get('q'): qs=qs.filter(id__icontains=request.GET['q'])
    if request.GET.get('state')=='Blocked': qs=qs.filter(blocked=True)
    return shell(request,'accounts.html','Accounts',page=Paginator(qs,25).get_page(request.GET.get('page')))

@login_required
def account(request,pk):
    obj=get_object_or_404(Account,pk=pk)
    if request.method=='POST':
        reason=request.POST.get('reason','').strip()
        action=request.POST.get('action')
        if not reason or action not in ['block','unblock']: messages.error(request,'Choose an action and enter a reason for the audit trail.')
        else:
            with atomic.atomic():
                obj=Account.objects.select_for_update().get(pk=pk)
                before='Blocked' if obj.blocked else 'Active'
                obj.blocked=action=='block'; obj.save()
                AuditEvent.objects.create(actor=request.user,action='Account restriction changed',target=pk,reason=reason,before=before,after='Blocked' if obj.blocked else 'Active')
            messages.success(request,'Account updated. Previously blocked transfers stay blocked.')
            return redirect('account',pk=pk)
    history=Transaction.objects.filter(Q(sender=obj)|Q(recipient=obj))
    return shell(request,'account.html','Account profile',account=obj,history=history[:40],events=AuditEvent.objects.filter(target=pk).order_by('-created'),devices=obj.sent.values('device').distinct(),partners=history.values('sender_id','recipient_id').distinct()[:10])

@login_required
def algorithms(request):
    run=DetectionRun.objects.order_by('-pk').first()
    benchmark_path=settings.BASE_DIR/'artifacts/benchmark.json'
    benchmark=json.loads(benchmark_path.read_text()) if benchmark_path.exists() else None
    return shell(request,'algorithms.html','Algorithm results',run=run,benchmark=benchmark)

@staff
@require_POST
def run_analysis(request):
    try:
        run=analyze(request.user,int(request.POST.get('trees',32)),float(request.POST.get('eps',1.8)),int(request.POST.get('k',10)))
        messages.success(request,f'Run #{run.pk} completed in {run.duration:.1f}s. Existing operational decisions preserved.')
    except (ValueError,OverflowError) as e: messages.error(request,str(e))
    return redirect('algorithms')

@staff
@require_POST
def import_data(request):
    count=import_dataset(settings.BASE_DIR/'data/generated/secflow_transactions.csv')
    AuditEvent.objects.create(actor=request.user,action='Dataset imported',target='dataset',reason=f'{count} selected rows; idempotent import')
    messages.success(request,f'Dataset checked: {count} selected rows. Existing transactions retained.')
    return redirect('algorithms')

@login_required
def audit(request):
    return shell(request,'audit.html','Audit trail',page=Paginator(AuditEvent.objects.select_related('actor').order_by('-created'),40).get_page(request.GET.get('page')))

@login_required
def export(request):
    if request.GET.get('kind')=='benchmark':
        path=settings.BASE_DIR/'artifacts/benchmark.json'
        response=HttpResponse(path.read_text() if path.exists() else '{}',content_type='application/json')
        response['Content-Disposition']='attachment; filename=secflow-benchmark.json'
        return response
    if request.GET.get('kind')=='metrics':
        run=DetectionRun.objects.last()
        response=HttpResponse(json.dumps(run.metrics if run else {},indent=2),content_type='application/json')
        response['Content-Disposition']='attachment; filename="secflow-metrics.json"'
        return response
    response=HttpResponse(content_type='text/csv')
    response['Content-Disposition']='attachment; filename="secflow-transactions.csv"'
    writer=csv.writer(response); writer.writerow(['id','sender','recipient','amount','currency','origin','risk','decision'])
    for row in Transaction.objects.values_list('id','sender_id','recipient_id','amount','currency','origin','risk','decision').iterator():
        writer.writerow(["'"+str(v) if str(v).startswith(('=','+','-','@')) else v for v in row])
    return response

@login_required
def simulate(request):
    from .forms import SimulationForm
    import uuid
    form=SimulationForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        if Transaction.objects.filter(origin='Generated scenario').count()<200:
            messages.error(request,'Import the demonstration dataset first.')
        else:
            with atomic.atomic():
                data=form.cleaned_data
                tx=Transaction.objects.create(id='LIVE_'+uuid.uuid4().hex[:12],sender=data['sender'],recipient=data['recipient'],amount=data['amount'],timestamp=(Transaction.objects.aggregate(t=Max('timestamp'))['t'] or 0)+10,kind='TRANSFER',origin='Generated scenario',currency='DEMO_UNIT',device=data['device'],failed_logins=data['failed_logins'],truth=None,metadata={'source':'Manual simulation; no ground truth label'})
                analyze(request.user)
                AuditEvent.objects.create(actor=request.user,action='Transfer simulated',target=tx.pk,reason='Manual local demonstration; no money moved')
            messages.success(request,'Simulation evaluated. No real money was moved.')
            return redirect('detail',pk=tx.pk)
    return shell(request,'simulate.html','Simulate transfer',form=form)
