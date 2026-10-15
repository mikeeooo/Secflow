"""Small server-rendered views: validate input, call a workflow, render a page."""
import csv
import json
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Max, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from detection.pipeline import contributions, rules, parameters
from detection.forecast import estimate
from .forms import SimulationForm
from .models import Account, AnalysisJob, Assessment, AuditEvent, CaseNote, DetectionRun, FraudCase, Transaction
from .services import import_dataset
from .background import enqueue_transfer, enqueue_replay

staff = user_passes_test(lambda user: user.is_active and user.is_staff)


def shell(request, template, title, **context):
    auto_refresh = request.resolver_match.url_name in ['dashboard', 'transactions', 'accounts']
    return render(request, template, {'title': title, 'auto_refresh': auto_refresh,
                                     'monitor_revision': monitor_revision() if auto_refresh else '', **context})


def latest_replay():
    return DetectionRun.objects.exclude(parameters__mode='single').order_by('-pk').first()


def filtered_transactions(request):
    rows = Transaction.objects.select_related('sender', 'recipient')
    query = request.GET.get('q', '').strip()
    if query:
        rows = rows.filter(Q(id__icontains=query) | Q(sender__id__icontains=query) | Q(recipient__id__icontains=query) | Q(sender__display_name__icontains=query) | Q(recipient__display_name__icontains=query))
    rows = rows.filter(origin=request.GET.get('origin') or 'Generated scenario')
    if request.GET.get('decision'):
        rows = rows.filter(decision=request.GET['decision'])
    return rows


@login_required
def dashboard(request):
    rows = Transaction.objects.filter(origin='Generated scenario')
    counts = {row['decision']: row['n'] for row in rows.values('decision').annotate(n=Count('id'))}
    buckets = list(rows.extra(select={'day': 'timestamp / 86400'}).values('day').annotate(total=Count('id')).order_by('day'))
    peak = max([bucket['total'] for bucket in buckets] or [1])
    for bucket in buckets:
        bucket['height'] = round(bucket['total'] / peak * 100)
    open_cases = FraudCase.objects.select_related('transaction__sender').filter(transaction__origin='Generated scenario').exclude(status='Resolved')
    return shell(
        request, 'dashboard.html', 'Monitorizare MIA', total=rows.count(),
        review=open_cases.filter(transaction__decision='Review').count(),
        open_cases=open_cases.count(), blocked=Account.objects.filter(id__startswith='SIM_', blocked=True).count(),
        allowed=counts.get('Allow', 0), pending=counts.get('Pending', 0),
        cases=open_cases.order_by('-transaction__risk', 'pk')[:6], buckets=buckets, run=latest_replay(),
        recent=list(rows.select_related('sender', 'recipient').order_by('-timestamp')[:5]),
        simulated_now=rows.order_by('-timestamp').first(),
        queued=AnalysisJob.objects.filter(status__in=['queued','running']).count(),
        impact=list(rows.exclude(truth=None).values('currency').annotate(
            blocked_fraud=Sum('amount', filter=Q(truth=True, decision='Block')),
            allowed_fraud=Sum('amount', filter=Q(truth=True, decision='Allow')),
            legitimate_blocks=Count('id', filter=Q(truth=False, decision='Block')))),
        sums=list(rows.values('currency').annotate(value=Sum('amount'))),
        origins=list(rows.values('origin').annotate(n=Count('id'))),
    )


@login_required
def transactions(request):
    rows = filtered_transactions(request)
    return shell(request, 'transactions.html', 'Tranzacții',
                 page=Paginator(rows, 25).get_page(request.GET.get('page')),
                 q=request.GET.get('q', '').strip())


@login_required
def detail(request, pk):
    tx = get_object_or_404(Transaction.objects.select_related('sender', 'recipient'), pk=pk)
    assessment = tx.assessments.order_by('-run_id').first()
    parts = []
    if assessment and tx.evidence:
        rule_score, _ = rules(tx.evidence)
        parts = contributions(assessment.forest, assessment.lof, assessment.cluster, rule_score)
    return shell(request, 'detail.html', 'Detaliile tranzacției', tx=tx, assessment=assessment, parts=parts,
                 case=FraudCase.objects.filter(transaction=tx).first(),
                 job=AnalysisJob.objects.filter(transaction=tx).order_by('-pk').first())


@login_required
def cases(request):
    rows = FraudCase.objects.select_related('transaction__sender', 'assignee').filter(transaction__origin='Generated scenario').order_by('-transaction__timestamp', '-pk')
    if request.GET.get('q'):
        rows = rows.filter(Q(transaction__sender__id__icontains=request.GET['q']) |
                           Q(transaction__sender__display_name__icontains=request.GET['q']))
    if request.GET.get('status') == 'unresolved':
        rows = rows.exclude(status='Resolved')
    elif request.GET.get('status'):
        rows = rows.filter(status=request.GET['status'])
    return shell(request, 'cases.html', 'Cazuri', page=Paginator(rows, 25).get_page(request.GET.get('page')))


@login_required
def case_detail(request, pk):
    case = get_object_or_404(FraudCase.objects.select_related('transaction__sender', 'transaction__recipient'), pk=pk)
    if request.method == 'POST':
        status = request.POST.get('status')
        outcome = request.POST.get('outcome', '')
        note = request.POST.get('note', '').strip()
        if (status not in ['Open', 'Investigating', 'Resolved']
                or outcome not in ['', 'Confirmed fraud', 'False positive', 'Inconclusive']
                or (status == 'Resolved' and not outcome) or not note):
            messages.error(request, 'Adaugă o notă și alege o concluzie pentru rezolvarea cazului.')
        else:
            with transaction.atomic():
                before = case.status
                case.status = status
                case.outcome = outcome if status == 'Resolved' else ''
                case.assignee = request.user
                case.closed_at = (Transaction.objects.aggregate(t=Max('timestamp'))['t'] or case.transaction.timestamp) if status == 'Resolved' else None
                case.save()
                CaseNote.objects.create(case=case, author=request.user, text=note)
                AuditEvent.objects.create(actor=request.user, action='Case updated', target=str(case.pk),
                                          reason=note, before=before, after=status)
            messages.success(request, 'Investigația a fost salvată. Restricția contului se gestionează separat.')
            return redirect('case', pk=pk)
    return shell(request, 'case.html', 'Investigație', case=case,
                 selected_status=request.POST.get('status', case.status),
                 selected_outcome=request.POST.get('outcome', case.outcome),
                 draft_note=request.POST.get('note', ''), notes=case.notes.select_related('author').order_by('-created'))


@login_required
def accounts(request):
    rows = Account.objects.filter(id__startswith='SIM_').annotate(transfer_count=Count('sent', distinct=True)).order_by('-risk', 'display_name', 'id')
    if request.GET.get('q'):
        rows = rows.filter(Q(id__icontains=request.GET['q']) | Q(display_name__icontains=request.GET['q']))
    if request.GET.get('state') == 'Blocked':
        rows = rows.filter(blocked=True)
    return shell(request, 'accounts.html', 'Clienți și conturi', page=Paginator(rows, 25).get_page(request.GET.get('page')))


@login_required
def account(request, pk):
    obj = get_object_or_404(Account, pk=pk)
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        action = request.POST.get('action')
        if not reason or action not in ['block', 'unblock']:
            messages.error(request, 'Alege acțiunea și completează motivul modificării.')
        else:
            with transaction.atomic():
                obj = Account.objects.get(pk=pk)
                before = 'Blocked' if obj.blocked else 'Active'
                obj.blocked = action == 'block'
                obj.save(update_fields=['blocked'])
                AuditEvent.objects.create(actor=request.user, action='Account restriction changed', target=pk,
                                          reason=reason, before=before, after='Blocked' if obj.blocked else 'Active')
            messages.success(request, 'Contul a fost actualizat. Tranzacțiile refuzate anterior rămân blocate.')
            return redirect('account', pk=pk)
    history = Transaction.objects.select_related('sender', 'recipient').filter(Q(sender=obj) | Q(recipient=obj))
    current = Transaction.objects.filter(origin='Generated scenario').aggregate(t=Max('timestamp'))['t'] or 0
    profile_cases = FraudCase.objects.filter(transaction__sender=obj).select_related('transaction').order_by('-transaction__timestamp')
    forecast = estimate(list(obj.sent.filter(timestamp__gte=current - 21600).values_list('timestamp','risk')), current)
    return shell(request, 'account.html', 'Profil client', account=obj, history=history[:10],
                 events=AuditEvent.objects.filter(target=pk).order_by('-created'),
                 devices=obj.sent.values('device').distinct(), forecast=forecast, profile_cases=profile_cases[:8],
                 sent_count=obj.sent.count(), received_count=obj.received.count(),
                 prior_cases=profile_cases.filter(status='Resolved').count())


@login_required
def algorithms(request):
    benchmark_path = settings.BASE_DIR / 'artifacts/benchmark.json'
    try:
        benchmark = json.loads(benchmark_path.read_text())
    except (OSError, ValueError):
        benchmark = None
    run = latest_replay()
    available = run.metrics if run else {}
    selected_origin = request.GET.get('origin', 'Generated scenario')
    if selected_origin not in available:
        selected_origin = next(iter(available), '')
    return shell(request, 'algorithms.html', 'Rezultate de detecție', run=run, benchmark=benchmark,
                 selected_origin=selected_origin, selected_result=available.get(selected_origin, {}))


@staff
@require_POST
def run_analysis(request):
    try:
        config = parameters(int(request.POST.get('trees',32)), float(request.POST.get('eps',1.8)), int(request.POST.get('k',10)))
        enqueue_replay(request.user, trees=config['trees'], eps=config['eps'], k=config['k'])
        messages.success(request, 'Analiza a fost programată în fundal.')
    except (ValueError, OverflowError) as error:
        messages.error(request, str(error))
    return redirect('algorithms')


@staff
@require_POST
def import_data(request):
    try:
        count = import_dataset(settings.BASE_DIR / 'data/generated/secflow_transactions.csv')
        if count:
            enqueue_replay(request.user)
        AuditEvent.objects.create(actor=request.user, action='Dataset imported', target='dataset',
                                  reason=f'{count} selected rows; idempotent import')
        messages.success(request, f'Set verificat: {count} rânduri selectate. Tranzacțiile existente au fost păstrate.')
    except (OSError, ValueError) as error:
        messages.error(request, f'Importul nu a fost finalizat: {error}')
    return redirect('algorithms')


@login_required
def audit(request):
    rows = AuditEvent.objects.select_related('actor').order_by('-created')
    return shell(request, 'audit.html', 'Jurnal de activitate', page=Paginator(rows, 40).get_page(request.GET.get('page')))


@login_required
def export(request):
    if request.GET.get('kind') == 'benchmark':
        path = settings.BASE_DIR / 'artifacts/benchmark.json'
        response = HttpResponse(path.read_text() if path.exists() else '{}', content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename=secflow-benchmark.json'
        return response
    if request.GET.get('kind') == 'metrics':
        run = latest_replay()
        response = HttpResponse(json.dumps(run.metrics if run else {}, indent=2), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename=secflow-metrics.json'
        return response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=secflow-transactions.csv'
    writer = csv.writer(response)
    writer.writerow(['id', 'sender', 'recipient', 'amount', 'currency', 'origin', 'risk', 'decision'])
    rows = filtered_transactions(request).values_list('id', 'sender_id', 'recipient_id', 'amount', 'currency', 'origin', 'risk', 'decision')
    for row in rows.iterator():
        writer.writerow(["'" + str(value) if str(value).startswith(('=', '+', '-', '@')) else value for value in row])
    return response


@login_required
def simulate(request):
    form = SimulationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                data = form.cleaned_data
                tx = Transaction.objects.create(
                    id='LIVE_' + uuid.uuid4().hex[:12], sender=data['sender'], recipient=data['recipient'],
                    amount=data['amount'], timestamp=(Transaction.objects.aggregate(t=Max('timestamp'))['t'] or 0) + 10,
                    kind='TRANSFER', origin='Generated scenario', currency='DEMO_UNIT', device=data['device'],
                    failed_logins=data['failed_logins'], truth=None,
                    metadata={'source': 'Manual simulation; no ground truth label'})
                enqueue_transfer(tx, request.user)
                AuditEvent.objects.create(actor=request.user, action='Transfer simulated', target=tx.pk,
                                          reason='Simulare locală manuală; nu s-au transferat bani reali')
            messages.success(request, 'Cererea a fost primită. Analiza automată se desfășoară în fundal.')
            return redirect('detail', pk=tx.pk)
        except ValueError as error:
            messages.error(request, str(error))
    return shell(request, 'simulate.html', 'Simulează o tranzacție', form=form)


@login_required
def analysis_status(request, pk):
    tx = get_object_or_404(Transaction, pk=pk)
    job = AnalysisJob.objects.filter(transaction=tx).order_by('-pk').first()
    return JsonResponse({'status': job.status if job else 'completed',
                         'decision': tx.decision_label, 'risk': tx.risk})


def monitor_revision():
    latest = Transaction.objects.filter(origin='Generated scenario').aggregate(t=Max('timestamp'), n=Count('pk'))
    assessment = Assessment.objects.aggregate(pk=Max('pk'))['pk'] or 0
    event = AuditEvent.objects.aggregate(pk=Max('pk'))['pk'] or 0
    return f"{latest['n']}:{latest['t']}:{assessment}:{event}"


@login_required
def monitor_status(request):
    return JsonResponse({'revision': monitor_revision()})
