"""Small server-rendered views: validate input, call a workflow, render a page."""
import csv
import json
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Max, Q, OuterRef, Subquery, IntegerField
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from detection.mia import ORIGIN
from .playback import active_origin
from .monitoring import snapshot
from .models import DemoPlayback

from detection.pipeline import parameters
from detection.forecast import estimate
from .forms import SimulationForm
from .models import Account, AnalysisJob, Assessment, AuditEvent, CaseNote, DetectionRun, FraudCase, Transaction
from .services import import_dataset
from .background import enqueue_transfer, enqueue_replay

staff = user_passes_test(lambda user: user.is_active and user.is_staff)


def shell(request, template, title, **context):
    auto_refresh = request.resolver_match.url_name in ['transactions', 'accounts']
    return render(request, template, {'title': title, 'auto_refresh': auto_refresh,
                                     'monitor_revision': monitor_revision() if auto_refresh else '', **context})


def latest_replay():
    return DetectionRun.objects.exclude(parameters__mode='single').order_by('-pk').first()


def historical_mia_report():
    try:
        report = json.loads((settings.BASE_DIR/'artifacts/mia-continuous-evaluation.json').read_text())
        from detection.risk import VERSION
        return report if report['parameters']['policy_version'] == VERSION else None
    except (OSError, ValueError, KeyError):
        return None


def filtered_transactions(request):
    rows = Transaction.objects.select_related('sender', 'recipient').filter(visible=True)
    query = request.GET.get('q', '').strip()
    if query:
        rows = rows.filter(Q(id__icontains=query) | Q(sender__id__icontains=query) | Q(recipient__id__icontains=query) | Q(sender__display_name__icontains=query) | Q(recipient__display_name__icontains=query))
    rows = rows.filter(origin=request.GET.get('origin') or active_origin())
    if request.GET.get('decision'):
        rows = rows.filter(decision=request.GET['decision'])
    return rows


def period(request):
    return {'1': 1, '6': 6, '24': 24}.get(request.GET.get('hours'), 6)


@login_required
def dashboard(request):
    return shell(request, 'dashboard.html', 'Monitorizare MIA', **snapshot(period(request)))


@login_required
def dashboard_data(request):
    context = snapshot(period(request))
    return JsonResponse({'html': render_to_string('dashboard_panels.html', context, request=request),
                         'playback': context['state'].status if context['state'] else 'unavailable'})


@login_required
@require_POST
@transaction.atomic
def playback_control(request):
    action = request.POST.get('action')
    if action not in ('running', 'paused'):
        return HttpResponse(status=400)
    state = get_object_or_404(DemoPlayback, pk=1)
    if state.status == 'completed' and action == 'running':
        from .playback import repeat_stream
        repeat_stream()
    else:
        state.status = action
        state.save(update_fields=['status'])
    state.refresh_from_db()
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'status': state.status})
    return redirect('dashboard')


@login_required
def metrics_endpoint(request):
    data = snapshot()
    gauges = {'transfers': data['total'], 'alerts': data['alerts'], 'queue_depth': data['queued'],
              'worker_up': int(data['healthy']), 'analysis_latency_ms': data['latency'] or 0,
              'failed_jobs': data['failed']}
    text = ''.join(f'# TYPE secflow_{name} gauge\nsecflow_{name} {value}\n' for name,value in gauges.items())
    return HttpResponse(text, content_type='text/plain; version=0.0.4; charset=utf-8')


@login_required
def transactions(request):
    rows = filtered_transactions(request)
    return shell(request, 'transactions.html', 'Tranzacții',
                 page=Paginator(rows, 25).get_page(request.GET.get('page')),
                 q=request.GET.get('q', '').strip())


@login_required
def detail(request, pk):
    tx = get_object_or_404(Transaction.objects.select_related('sender', 'recipient'), pk=pk, visible=True)
    assessment = tx.assessments.order_by('-run_id').first()
    evidence = tx.evidence
    observations = []
    if evidence:
        if evidence.get('amount_ratio', 1) > 3: observations.append(f"Suma depășește de {evidence['amount_ratio']:.1f} ori media anterioară.")
        if evidence.get('new_device'): observations.append('Cerere de pe un dispozitiv nou.')
        if evidence.get('failed_logins', 0): observations.append(f"Autentificări eșuate: {evidence['failed_logins']}.")
        if evidence.get('recent_count', 0) >= 3: observations.append(f"Transferuri în ultimele 5 minute: {evidence['recent_count']}.")
    return shell(request, 'detail.html', 'Detaliile tranzacției', tx=tx, assessment=assessment, observations=observations, risk_info=assessment.explanation if assessment else {},
                 case=FraudCase.objects.filter(transaction=tx).first(),
                 job=AnalysisJob.objects.filter(transaction=tx).order_by('-pk').first())


@login_required
def cases(request):
    rows = FraudCase.objects.select_related('transaction__sender', 'assignee').filter(transaction__origin=active_origin(), transaction__visible=True).order_by('-transaction__timestamp', '-pk')
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
    case = get_object_or_404(FraudCase.objects.select_related('transaction__sender', 'transaction__recipient'), pk=pk, transaction__visible=True)
    case_errors = {}
    if request.method == 'POST':
        status = request.POST.get('status')
        outcome = request.POST.get('outcome', '')
        note = request.POST.get('note', '').strip()
        if status not in ['Open', 'Investigating', 'Resolved']:
            case_errors['status'] = 'Alege o stare validă pentru caz.'
        if outcome not in ['', 'Confirmed fraud', 'False positive', 'Inconclusive']:
            case_errors['outcome'] = 'Alege o concluzie validă.'
        elif status == 'Resolved' and not outcome:
            case_errors['outcome'] = 'Alege o concluzie pentru a rezolva cazul.'
        if not note:
            case_errors['note'] = 'Adaugă dovezile verificate în nota de investigație.'
        if not case_errors:
            with transaction.atomic():
                before = case.status
                case.status = status
                case.outcome = outcome if status == 'Resolved' else ''
                case.assignee = request.user
                case.closed_at = (Transaction.objects.filter(origin=case.transaction.origin, visible=True).aggregate(t=Max('timestamp'))['t'] or case.transaction.timestamp) if status == 'Resolved' else None
                case.save()
                CaseNote.objects.create(case=case, author=request.user, text=note)
                AuditEvent.objects.create(actor=request.user, action='Case updated', target=str(case.pk),
                                          reason=note, before=before, after=status)
            messages.success(request, 'Investigația a fost salvată. Restricția contului se gestionează separat.')
            return redirect('case', pk=pk)
    return shell(request, 'case.html', 'Investigație', case=case,
                 case_errors=case_errors, selected_status=request.POST.get('status', case.status),
                 selected_outcome=request.POST.get('outcome', case.outcome),
                 draft_note=request.POST.get('note', ''), notes=case.notes.select_related('author').order_by('-created'))


@login_required
def accounts(request):
    latest = Transaction.objects.filter(sender_id=OuterRef('pk'), visible=True, risk__isnull=False).order_by('-timestamp','-pk')
    rows = Account.objects.filter(id__startswith='SIM_MIA_' if active_origin() == ORIGIN else 'SIM_').annotate(
        transfer_count=Count('sent', filter=Q(sent__visible=True), distinct=True),
        latest_score=Coalesce(Subquery(latest.values('risk_explanation__score')[:1], output_field=IntegerField()),
                              Subquery(latest.values('risk')[:1]), output_field=IntegerField()),
    ).order_by('-latest_score', 'display_name', 'id')
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
    history = Transaction.objects.select_related('sender', 'recipient').filter(Q(sender=obj) | Q(recipient=obj), visible=True)
    current = Transaction.objects.filter(origin=active_origin(), visible=True).aggregate(t=Max('timestamp'))['t'] or 0
    profile_cases = FraudCase.objects.filter(transaction__sender=obj, transaction__visible=True).select_related('transaction').order_by('-transaction__timestamp')
    recent = list(obj.sent.filter(visible=True, timestamp__gte=current - 21600))
    forecast = estimate([(tx.timestamp, tx.display_risk) for tx in recent], current, threshold=45)
    latest_tx = obj.sent.filter(visible=True, risk__isnull=False).order_by('-timestamp','-pk').first()
    return shell(request, 'account.html', 'Profil client', account=obj, history=history[:10],
                 latest_tx=latest_tx, risk_info=latest_tx.risk_explanation if latest_tx else {},
                 events=AuditEvent.objects.filter(target=pk).order_by('-created'),
                 devices=obj.sent.filter(visible=True).values('device').distinct(), forecast=forecast, profile_cases=profile_cases[:8],
                 sent_count=obj.sent.filter(visible=True).count(), received_count=obj.received.filter(visible=True).count(),
                 prior_cases=profile_cases.filter(status='Resolved').count())


@login_required
def algorithms(request):
    run = latest_replay()
    available = run.metrics if run else {}
    selected_origin = request.GET.get('origin', active_origin())
    if selected_origin not in available:
        selected_origin = next(iter(available), '')
    selected = available.get(selected_origin, {})
    evaluation_scope = 'Evaluarea ultimei reanalizări a istoricului vizibil.'
    if selected_origin == ORIGIN and (report := historical_mia_report()):
        selected = {'methods': {'test': report['methods']}}
        evaluation_scope = 'Testul istoric inițial de 768 de cereri, separat de fluxul redat.'
    return shell(request, 'algorithms.html', 'Rezultate de detecție', run=run,
                 selected_origin=selected_origin, selected_result=selected, evaluation_scope=evaluation_scope)



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
        payload = run.metrics if run else {}
        if active_origin() == ORIGIN and (report := historical_mia_report()):
            payload = {'historical_test': report, 'latest_visible_replay': payload}
        response = HttpResponse(json.dumps(payload, indent=2), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename=secflow-metrics.json'
        return response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=secflow-transactions.csv'
    writer = csv.writer(response)
    writer.writerow(['id', 'sender', 'recipient', 'amount', 'currency', 'origin', 'risk_current', 'decision_initial'])
    rows = filtered_transactions(request)
    for tx in rows.iterator():
        row = (tx.pk, tx.sender_id, tx.recipient_id, tx.amount, tx.currency, tx.origin, tx.display_risk, tx.decision)
        writer.writerow(["'" + str(value) if str(value).startswith(('=', '+', '-', '@')) else value for value in row])
    return response


@login_required
def simulate(request):
    form = SimulationForm(request.POST if request.method == 'POST' else None)
    if active_origin() == ORIGIN:
        for field in ('sender', 'recipient'):
            form.fields[field].queryset = Account.objects.filter(id__startswith='SIM_MIA_').order_by('display_name')
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                data = form.cleaned_data
                tx = Transaction.objects.create(
                    id='LIVE_' + uuid.uuid4().hex[:12], sender=data['sender'], recipient=data['recipient'],
                    amount=data['amount'], timestamp=(Transaction.objects.filter(origin=active_origin(), visible=True).aggregate(t=Max('timestamp'))['t'] or 0) + 1,
                    kind='TRANSFER', origin=active_origin(), currency='MDL' if active_origin() == ORIGIN else 'DEMO_UNIT', device=data['device'],
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
    tx = get_object_or_404(Transaction, pk=pk, visible=True)
    job = AnalysisJob.objects.filter(transaction=tx).order_by('-pk').first()
    return JsonResponse({'status': job.status if job else 'completed',
                         'decision': tx.decision_label, 'risk': tx.display_risk})


def monitor_revision():
    latest = Transaction.objects.filter(origin=active_origin(), visible=True).aggregate(t=Max('timestamp'), n=Count('pk'))
    assessment = Assessment.objects.aggregate(pk=Max('pk'))['pk'] or 0
    event = AuditEvent.objects.aggregate(pk=Max('pk'))['pk'] or 0
    return f"{latest['n']}:{latest['t']}:{assessment}:{event}"


@login_required
def monitor_status(request):
    return JsonResponse({'revision': monitor_revision()})
