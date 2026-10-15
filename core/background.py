"""A persistent SQLite queue. One worker evaluates requests outside HTTP views."""
from django.db import transaction
from django.utils import timezone

from .models import AnalysisJob
from .services import analyze, assess_transfer


def enqueue_transfer(tx, actor=None):
    job, _ = AnalysisJob.objects.get_or_create(kind='single', transaction=tx, defaults={'actor': actor})
    return job


def enqueue_replay(actor=None, **config):
    existing = AnalysisJob.objects.filter(kind='replay', status__in=['queued', 'running']).first()
    if existing:
        return existing
    return AnalysisJob.objects.create(kind='replay', actor=actor, parameters=config)


def process_next():
    job = AnalysisJob.objects.filter(status='queued').order_by('pk').first()
    if not job:
        return False
    claimed = AnalysisJob.objects.filter(pk=job.pk, status='queued').update(status='running', started=timezone.now())
    if not claimed:
        return True
    try:
        # Scoring and completion commit together. A crash cannot leave half a run.
        with transaction.atomic():
            if job.kind == 'single':
                assess_transfer(job.transaction, job.actor)
            else:
                analyze(job.actor, **job.parameters)
            AnalysisJob.objects.filter(pk=job.pk).update(status='completed', finished=timezone.now(), error='')
    except Exception as error:
        # Diagnostics are retained for the administrator; the worker keeps running.
        AnalysisJob.objects.filter(pk=job.pk).update(status='failed', finished=timezone.now(), error=str(error))
    return True
