import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from django.conf import settings
from core.services import import_dataset, analyze
class Command(BaseCommand):
    help='Import a deterministic demo subset and run the actual algorithms.'
    def add_arguments(self,parser):
        parser.add_argument('--paysim-limit',type=int,default=2000)
        parser.add_argument('--skip-analysis',action='store_true')
    def handle(self,*args,**opts):
        password=os.environ.get('SECFLOW_DEMO_PASSWORD')
        if not password: raise CommandError('Set SECFLOW_DEMO_PASSWORD before creating demo users.')
        group,_=Group.objects.get_or_create(name='Analyst')
        for name,admin in [('admin',True),('analyst',False)]:
            user,created=User.objects.get_or_create(username=name,defaults={'is_staff':admin,'is_superuser':admin})
            if created: user.set_password(password); user.save()
            if not admin: user.groups.add(group)
        count=import_dataset(settings.BASE_DIR/'data/generated/secflow_transactions.csv',opts['paysim_limit'])
        self.stdout.write(f'Imported {count} rows (idempotent).')
        if not opts['skip_analysis']:
            run=analyze(User.objects.get(username='admin'))
            self.stdout.write(f'Run {run.pk}: {run.count} assessments in {run.duration:.1f}s')
