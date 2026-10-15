from django.core.management.base import BaseCommand
from core.demo import prepare_profiles


class Command(BaseCommand):
    help = 'Adaugă identități fictive stabile și dosare istorice demonstrative, fără a modifica CSV-ul.'

    def handle(self, *args, **options):
        names, cases = prepare_profiles()
        self.stdout.write(f'Profiluri numite: {names}. Dosare istorice pregătite: {cases}.')
