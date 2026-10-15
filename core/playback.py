"""Replay an immutable synthetic stream through the real persistent scoring queue."""
from datetime import timedelta
import uuid
from django.db.models import Max

from django.db import transaction
from django.utils import timezone

from detection.mia import ORIGIN
from .models import AnalysisJob, DemoPlayback, Transaction


def active_origin():
    return ORIGIN if Transaction.objects.filter(origin=ORIGIN).exists() else 'Generated scenario'


@transaction.atomic
def tick(now=None):
    now = now or timezone.now()
    state = DemoPlayback.objects.filter(pk=1).first()
    if not state:
        return False
    state.heartbeat = now
    released = False
    # Backpressure: never advance the presentation clock past an unprocessed request.
    waiting = AnalysisJob.objects.filter(status__in=['queued', 'running']).exists()
    if state.status == 'running' and not waiting and (state.last_release is None or now - state.last_release >= timedelta(seconds=state.interval)):
        tx = Transaction.objects.filter(origin=ORIGIN, visible=False).order_by('timestamp', 'pk').first()
        if tx:
            current = Transaction.objects.filter(origin=ORIGIN, visible=True).aggregate(t=Max('timestamp'))['t'] or 0
            tx.timestamp = max(tx.timestamp, current + 1)
            tx.visible = True
            tx.save(update_fields=['visible', 'timestamp'])
            AnalysisJob.objects.get_or_create(kind='single', transaction=tx)
            state.released += 1
            state.last_release = now
            released = True
        else:
            state.status = 'completed'
    state.save()
    return released


@transaction.atomic
def repeat_stream():
    """A new cycle appends fresh requests; prior cases, notes and decisions survive."""
    from datasets.demo_mia import generate, HISTORY
    state = DemoPlayback.objects.get(pk=1)
    if state.status != 'completed' or Transaction.objects.filter(origin=ORIGIN, visible=False).exists():
        return False
    rows = generate()[HISTORY:]
    current = Transaction.objects.filter(origin=ORIGIN, visible=True).aggregate(t=Max('timestamp'))['t'] or 0
    offset = current + 60 - int(rows[0]['timestamp_seconds'])
    cycle = uuid.uuid4().hex[:10]
    Transaction.objects.bulk_create([
        Transaction(id=f'MIA_{cycle}_{index:03}', sender_id=row['nameOrig'], recipient_id=row['nameDest'],
                    amount=row['amount'], timestamp=int(row['timestamp_seconds'])+offset, kind='TRANSFER',
                    origin=ORIGIN, currency='MDL', device=row['device_id'],
                    failed_logins=row['failed_login_attempts'], truth=bool(row['ground_truth_fraud']),
                    metadata={**row, 'cycle': cycle}, visible=False)
        for index,row in enumerate(rows)])
    state.status, state.last_release, state.released = 'running', None, 0
    state.save(update_fields=['status','last_release','released'])
    return True
