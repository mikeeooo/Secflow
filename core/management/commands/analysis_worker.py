"""Run one lightweight background worker; no Redis or Celery required."""
import fcntl
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections, OperationalError

from core.background import process_next
from core.playback import tick
from core.models import AnalysisJob


class Command(BaseCommand):
    help = 'Procesează în fundal coada persistentă de analize.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Procesează o singură cerere și încheie.')

    def handle(self, *args, **options):
        lock_path = Path(settings.DATABASES['default']['NAME']).parent / '.secflow-worker.lock'
        with lock_path.open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise CommandError('Un proces de analiză rulează deja pentru această bază.') from error
            # The exclusive process lock makes recovery safe after an interrupted worker.
            recovered = AnalysisJob.objects.filter(status='running').update(status='queued', started=None)
            self.stdout.write(f'Analiză în fundal activă. Cereri recuperate: {recovered}')
            try:
                while True:
                    close_old_connections()
                    try:
                        tick()
                        worked = process_next()
                    except OperationalError as error:
                        if 'locked' not in str(error).lower():
                            raise
                        worked = False  # A concurrent analyst write can finish; retry the durable queue.
                    if options['once']:
                        return
                    if not worked:
                        time.sleep(1)
            except KeyboardInterrupt:
                self.stdout.write('Procesul de analiză a fost oprit. Coada rămâne salvată.')
