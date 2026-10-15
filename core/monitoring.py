"""Read-only dashboard projections. No model fitting occurs in HTTP requests."""
from datetime import timedelta

from django.db.models import Count, Max, Q, Sum
from django.utils import timezone

from detection.mia import ORIGIN
from .models import AnalysisJob, DemoPlayback, DetectionRun, FraudCase, SIMULATION_START, Transaction
from .playback import active_origin


def snapshot(hours=6):
    origin = active_origin()
    all_rows = Transaction.objects.filter(origin=origin, visible=True)
    now = all_rows.aggregate(t=Max('timestamp'))['t'] or 0
    start = now - hours * 3600
    rows = all_rows.filter(timestamp__gt=start)
    values = rows.aggregate(total=Count('pk'), alerts=Count('pk', filter=Q(decision__in=['Review','Block'])),
                            blocked=Count('pk', filter=Q(decision='Block')), amount=Sum('amount'),
                            pending=Count('pk', filter=Q(decision='Pending', features=[])),
                            reference=Count('pk', filter=Q(decision='Pending') & ~Q(features=[])))
    buckets = [{'total': 0, 'alerts': 0} for _ in range(12)]
    for timestamp, risk, explanation in rows.values_list('timestamp', 'risk', 'risk_explanation'):
        bucket = buckets[min(11, max(0, int((timestamp-start) / (hours*300))))]
        bucket['total'] += 1
        score = explanation.get('score', risk)
        bucket['alerts'] += score is not None and score >= explanation.get('review_threshold', 45)
    current_alerts = sum(bucket['alerts'] for bucket in buckets)
    peak = max([bucket['total'] for bucket in buckets] + [1])
    for index, bucket in enumerate(buckets):
        bucket.update(x=round(25+index*60, 1), y=round(152-bucket['total']/peak*125, 1),
                      ay=round(152-bucket['alerts']/peak*125, 1),
                      label=(SIMULATION_START+timedelta(seconds=start+(index+1)*hours*300)).strftime('%H:%M'))
    cases = FraudCase.objects.select_related('transaction__sender').filter(
        transaction__origin=origin, transaction__visible=True).exclude(status='Resolved')
    state = DemoPlayback.objects.filter(pk=1).first()
    healthy = bool(state and state.heartbeat and timezone.now()-state.heartbeat < timedelta(seconds=10))
    durations = list(DetectionRun.objects.filter(parameters__mode='single', parameters__source=origin).order_by('-pk').values_list('duration',flat=True)[:20])
    latency = round(sum(durations)/len(durations)*1000) if durations else None
    recent_jobs = AnalysisJob.objects.filter(kind='single', transaction__origin=origin)
    return {**values, 'alerts': current_alerts, 'hours': hours, 'origin': origin, 'simulated_now': SIMULATION_START+timedelta(seconds=now),
            'open_cases': cases.count(), 'cases': cases.order_by('-transaction__timestamp')[:5],
            'recent': rows.select_related('sender','recipient').order_by('-timestamp','-pk')[:5],
            'buckets': buckets, 'peak': peak,
            'line': ' '.join(f"{b['x']},{b['y']}" for b in buckets),
            'alert_line': ' '.join(f"{b['x']},{b['ay']}" for b in buckets),
            'state': state, 'healthy': healthy, 'latency': latency,
            'queued': AnalysisJob.objects.filter(status__in=['queued','running']).count(),
            'failed': recent_jobs.filter(status='failed').count(),
            'remaining': Transaction.objects.filter(origin=ORIGIN, visible=False).count(),
            'decisions': [{'name': name, 'count': count, 'percent': round(count/max(values['total'],1)*100), 'style': style}
                          for name, count, style in [
                              ('Permise', values['total']-values['alerts']-values['pending']-values['reference'], 'allow'),
                              ('De verificat', values['alerts']-values['blocked'], 'review'),
                              ('Blocate',values['blocked'],'block')]],
            'alert_rate': round(current_alerts/max(values['total'],1)*100,1)}
