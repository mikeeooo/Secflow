"""Fictional customer identities and labeled historical cases for the university demo."""
import hashlib

from django.db import transaction
from django.db.models import Max

from .models import Account, CaseNote, FraudCase, Transaction

FIRST_NAMES = ['Ion', 'Maria', 'Andrei', 'Elena', 'Victor', 'Ana', 'Mihai', 'Irina', 'Alexandru',
               'Diana', 'Sergiu', 'Natalia', 'Vasile', 'Cristina', 'Dumitru', 'Tatiana', 'Adrian',
               'Alina', 'Nicolae', 'Olga', 'Valeriu', 'Daniela', 'Petru', 'Marina', 'Gabriel', 'Sofia',
               'Constantin', 'Victoria', 'Eugen', 'Lilia', 'Radu', 'Doina', 'Pavel', 'Ecaterina']
LAST_NAMES = ['Rusu', 'Ciobanu', 'Ceban', 'Popa', 'Munteanu', 'Moraru', 'Rotaru', 'Balan', 'Cojocaru',
              'Ursu', 'Cazacu', 'Lungu', 'Bostan', 'Bîrsan', 'Grosu', 'Dumitru', 'Sîrbu', 'Botezatu',
              'Sandu', 'Pînzari', 'Mocanu', 'Bejan', 'Toma', 'Duca', 'Negură', 'Frunză', 'Drăgan',
              'Bratu', 'Ganea', 'Cărare', 'Burlacu', 'Pascari', 'Luca', 'Dobre']


def fictional_name(account_id):
    digest = hashlib.sha256(('secflow-fictional-' + account_id).encode()).digest()
    return f'{FIRST_NAMES[digest[0] % len(FIRST_NAMES)]} {LAST_NAMES[digest[1] % len(LAST_NAMES)]}'


@transaction.atomic
def prepare_profiles(history=True):
    accounts = list(Account.objects.filter(display_name=''))
    for account in accounts:
        account.display_name = fictional_name(account.pk)
    Account.objects.bulk_update(accounts, ['display_name'], batch_size=400)
    created = 0
    if history:
        current = Transaction.objects.filter(origin='Generated scenario').aggregate(t=Max('timestamp'))['t'] or 0
        candidates = FraudCase.objects.select_related('transaction').filter(
            status='Open', demo_history=False, notes__isnull=True,
            transaction__origin='Generated scenario', transaction__truth__isnull=False,
            transaction__timestamp__lt=current - 7200).order_by('transaction__timestamp', 'pk')
        for case in candidates:
            # Stable subset, avoiding analyst notes or already-investigated cases.
            if int(hashlib.sha256(case.transaction_id.encode()).hexdigest()[:4], 16) % 5:
                continue
            case.status = 'Resolved'
            case.outcome = 'Confirmed fraud' if case.transaction.truth else 'False positive'
            case.closed_at = case.transaction.timestamp + 3600
            case.demo_history = True
            case.save()
            CaseNote.objects.create(case=case, text=(
                'Dosar istoric demonstrativ. Concluzie preluată din eticheta scenariului generat: '
                + ('fraudă simulată confirmată.' if case.transaction.truth else 'activitate legitimă, alarmă falsă.')
                + ' Eticheta nu a fost folosită la calcularea riscului.'))
            created += 1
    return len(accounts), created
