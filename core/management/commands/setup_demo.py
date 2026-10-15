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
        parser.add_argument('--legacy', action='store_true', help='Importă vechiul experiment PaySim în locul portofoliului MIA.')
    def handle(self,*args,**opts):
        password=os.environ.get('SECFLOW_DEMO_PASSWORD')
        if not password and not all(User.objects.filter(username=name).exists() for name in ('admin', 'analyst')):
            raise CommandError('Set SECFLOW_DEMO_PASSWORD before creating demo users.')
        group,_=Group.objects.get_or_create(name='Analyst')
        for name,admin in [('admin',True),('analyst',False)]:
            user,created=User.objects.get_or_create(username=name,defaults={'is_staff':admin,'is_superuser':admin})
            if created: user.set_password(password); user.save()
            if not admin: user.groups.add(group)
        from datasets.demo_mia import write_dataset, ORIGIN
        from core.models import DemoPlayback
        path = settings.BASE_DIR/'data/generated/secflow_transactions.csv' if opts['legacy'] else write_dataset(settings.BASE_DIR/'data/generated')
        count=import_dataset(path,opts['paysim_limit'])
        self.stdout.write(f'Imported {count} rows (idempotent).')
        if not opts['skip_analysis']:
            run=analyze(User.objects.get(username='admin'), origin=None if opts['legacy'] else ORIGIN)
            self.stdout.write(f'Run {run.pk}: {run.count} assessments in {run.duration:.1f}s')
        from core.demo import prepare_profiles
        names, cases = prepare_profiles()
        self.stdout.write(f'Fictional profiles: {names}; historical demo cases: {cases}')

        if not opts['legacy']:
            DemoPlayback.objects.get_or_create(pk=1, defaults={'status': 'running'})
