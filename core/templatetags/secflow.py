"""Romanian presentation labels; stored decision codes stay stable."""
from django import template

register = template.Library()
LABELS = {
    'Allow': 'Permisă', 'Review': 'De verificat', 'Block': 'Blocată', 'Pending': 'Referință',
    'Open': 'Deschis', 'Investigating': 'În analiză', 'Resolved': 'Rezolvat',
    'Confirmed fraud': 'Fraudă confirmată', 'False positive': 'Alarmă falsă', 'Inconclusive': 'Neconcludent',
    'Generated scenario': 'Scenarii generate', 'validation': 'Validare', 'test': 'Test', 'manual': 'Simulare manuală',
    'Isolation Forest': 'Isolation Forest', 'Local Outlier Factor': 'Local Outlier Factor',
    'LOF': 'LOF', 'DBSCAN noise': 'DBSCAN · punct izolat', 'Behavior rules': 'Reguli de comportament',
    'Rules': 'Reguli', 'Algorithms only': 'Doar algoritmii', 'Combined': 'Scor combinat',
    'Amount exceeds eight times prior account mean': 'Suma depășește de opt ori media anterioară a contului.',
    'At least eight prior transfers within five minutes': 'Cel puțin opt cereri anterioare în cinci minute.',
    'New device after repeated failed sign-ins': 'Dispozitiv nou după cel puțin trei autentificări eșuate.',
    'Rapid outgoing activity after multiple incoming transfers': 'Transfer inițiat după mai multe încasări recente.',
    'Isolation Forest: short isolation path': 'Isolation Forest: tranzacția este ușor de separat de referință.',
    'LOF: lower density than reference neighbors': 'LOF: tranzacția se află într-o zonă mai rară decât vecinii săi.',
    'DBSCAN: noise in trailing 24-transfer window': 'DBSCAN: punct izolat în ultimele 24 de cereri.',
    'Limited prior account history': 'Contul are mai puțin de cinci cereri anterioare; istoricul este limitat.',
    'Sender already restricted in simulation': 'Contul expeditor era deja blocat în simulare.',
    'Active': 'Activ', 'Blocked': 'Blocat', 'Account restriction changed': 'Restricție modificată',
    'Automatic account restriction': 'Blocare automată', 'Analysis completed': 'Analiză finalizată',
    'Dataset imported': 'Date importate', 'Case updated': 'Caz actualizat', 'Transfer simulated': 'Tranzacție simulată',
}


@register.filter
def ro(value):
    return LABELS.get(str(value), value)


@register.filter
def percent(value):
    return f'{float(value) * 100:.1f}%'.replace('.', ',')
