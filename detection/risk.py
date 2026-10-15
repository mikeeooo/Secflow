"""An additive demonstration score. Every displayed point has a stored source."""
import math

VERSION = 'continuous-v2'
REVIEW = 45
HIGH = 60
BLOCK = 70


def number(value):
    return f'{value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def clamp(value):
    return max(0.0, min(1.0, value))


def explain(forest, lof, cluster, thresholds, evidence):
    """55 model points + 45 observable-behavior points; never read truth/scenario."""
    forest_strength = clamp(.5 + (forest-thresholds[0]) / (2*max(thresholds[0]-.35, .05)))
    lof_distance = max(0, lof-1)
    lof_strength = lof_distance / (lof_distance + max(thresholds[1]-1, .1))
    model_points = 25*forest_strength + 20*lof_strength + 10*(cluster == -1)
    count = evidence['history_count']
    ratio = evidence['amount_ratio']
    per_minute = evidence.get('recent_count_60', 0)
    recent = evidence['recent_count']
    failures = evidence['failed_logins']
    incoming = evidence['recent_incoming']
    device = evidence['new_device']
    beneficiary = evidence.get('new_beneficiary', False)
    amount_signal = clamp(math.log2(max(ratio, 1))/4) if count else 0
    factors = []

    def add(key, label, value, weight, detail, protective=False, known=True):
        factors.append({'key': key, 'label': label, 'points': round(value*weight, 2),
                        'maximum': weight, 'detail': detail, 'known': known,
                        'status': 'support' if protective and known else 'raised' if value >= .35 else 'watch' if value > 0 else 'neutral'})

    add('profile', 'Tiparul tranzacției', model_points/55, 55,
        'Abatere redusă față de tranzacțiile obișnuite.' if model_points < 15 else
        'Mai multe semnale statistice indică o abatere față de tranzacțiile obișnuite.' if model_points >= 35 else
        'Tiparul diferă parțial de activitatea din referință.', protective=model_points < 15)
    add('amount', 'Suma față de istoricul propriu', amount_signal, 12,
        f"{number(evidence.get('amount', 0))} MDL; {number(ratio)}× media anterioară de {number(evidence.get('prior_mean', 0))} MDL."
        if count else 'Nu există încă o medie proprie de comparație.',
        protective=ratio <= 1.5, known=count > 0)
    add('frequency', 'Frecvența transferurilor', clamp(max(per_minute/3, recent/6)), 8,
        f'{per_minute} cereri anterioare în 60 secunde; {recent} în 5 minute.', protective=recent == 0)
    add('device', 'Dispozitiv', float(device), 6,
        'Prima cerere de pe acest dispozitiv.' if device else 'Dispozitiv folosit anterior de acest client.', protective=not device)
    add('access', 'Autentificări eșuate', clamp(failures/6), 8,
        f'{failures} încercări eșuate asociate cererii.' if failures else 'Fără autentificări eșuate asociate cererii.', protective=not failures)
    add('beneficiary', 'Beneficiar', float(beneficiary), 4,
        'Prima plată către acest beneficiar.' if beneficiary else 'Beneficiar folosit anterior de acest client.', protective=not beneficiary)
    add('incoming', 'Încasări recente', clamp(incoming/4), 4,
        f'{incoming} cereri primite în ultimele 5 minute, înaintea acestei plăți.', protective=not incoming)
    add('history', 'Istoric disponibil', clamp((5-count)/5), 3,
        f'{count} cereri anterioare ale clientului; ' + ('istoric încă limitat.' if count < 5 else 'profil de comparație disponibil.'))
    # Sum the same stored values that the analyst can inspect; no random jitter.
    total = sum(factor['points'] for factor in factors)
    score = round(total)
    level = 'Ridicat' if score >= HIGH else 'Moderat' if score >= REVIEW else 'Scăzut'
    style = 'block' if score >= HIGH else 'review' if score >= REVIEW else 'allow'
    raised = sorted([factor for factor in factors if factor['status'] in ('raised','watch')], key=lambda factor: -factor['points'])
    priority = {'device':0, 'access':1, 'amount':2, 'beneficiary':3, 'frequency':4, 'incoming':5, 'profile':6}
    supportive = sorted([factor for factor in factors if factor['status'] == 'support'],
                        key=lambda factor: priority.get(factor['key'], 7))
    concrete = [factor for factor in raised if factor['key'] != 'profile']
    top = (concrete or raised)[:3]
    summary = (f"{top[0]['label']}: {top[0]['detail']}" if top and score >= REVIEW else
               'Semnalele cumulate sunt reduse; activitatea rămâne apropiată de profilul obișnuit.')
    return {'version': VERSION, 'score': score, 'level': level, 'style': style,
            'review_threshold': REVIEW, 'high_threshold': HIGH, 'block_threshold': BLOCK, 'total_points': round(total, 2),
            'factors': factors, 'drivers': top, 'supportive': supportive[:3],
            'summary': summary, 'rounding': round(score-total, 2)}
