"""One local command starts both the web app and its persistent queue worker."""
import subprocess
import sys

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Pornește aplicația locală și analiza automată în fundal.'

    def handle(self, *args, **options):
        worker = subprocess.Popen([sys.executable, str(settings.BASE_DIR / 'manage.py'), 'analysis_worker'])
        try:
            call_command('runserver', '127.0.0.1:8000', use_reloader=False)
        finally:
            worker.terminate()
            worker.wait()
