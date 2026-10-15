from django.db import models
from django.conf import settings
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

SIMULATION_START = datetime(2026, 10, 1, tzinfo=ZoneInfo('Europe/Chisinau'))

class Account(models.Model):
    id = models.CharField(primary_key=True,max_length=80)
    display_name = models.CharField(max_length=100, blank=True)
    blocked = models.BooleanField(default=False)
    risk = models.IntegerField(default=0)
    @property
    def public_id(self):
        import hashlib
        return 'MIA-' + hashlib.sha256(self.pk.encode()).hexdigest()[:8].upper()

    @property
    def name(self):
        return self.display_name or self.pk

    def __str__(self):
        return f'{self.name} · {self.public_id}'

class DatasetImport(models.Model):
    checksum = models.CharField(max_length=64,unique=True)
    name = models.CharField(max_length=200)
    rows = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)

class Transaction(models.Model):
    id = models.CharField(primary_key=True,max_length=80)
    sender = models.ForeignKey(Account,on_delete=models.PROTECT,related_name='sent')
    recipient = models.ForeignKey(Account,on_delete=models.PROTECT,related_name='received')
    amount = models.DecimalField(max_digits=18,decimal_places=2)
    timestamp = models.IntegerField(db_index=True)
    kind = models.CharField(max_length=30)
    origin = models.CharField(max_length=40)
    currency = models.CharField(max_length=20)
    device = models.CharField(max_length=80)
    failed_logins = models.IntegerField(default=0)
    truth = models.BooleanField(default=False,null=True)
    metadata = models.JSONField(default=dict)
    features = models.JSONField(default=list)
    evidence = models.JSONField(default=dict)
    risk_explanation = models.JSONField(default=dict)
    visible = models.BooleanField(default=True, db_index=True)
    risk = models.IntegerField(null=True)
    decision = models.CharField(max_length=20,default='Pending')
    class Meta: ordering = ['-timestamp','id']

    @property
    def display_risk(self):
        return self.risk_explanation.get('score', self.risk)

    @property
    def risk_summary(self):
        return self.risk_explanation.get('summary', '')

    @property
    def occurred_at(self):
        return SIMULATION_START + timedelta(seconds=self.timestamp)

    @property
    def currency_label(self):
        return 'MDL demo' if self.currency in ('DEMO_UNIT', 'MDL') else 'unități PaySim'

    @property
    def decision_label(self):
        if self.decision == 'Pending':
            return 'Referință' if self.features else 'În analiză'
        return {'Allow': 'Permisă', 'Review': 'De verificat', 'Block': 'Blocată'}[self.decision]

class DetectionRun(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    parameters = models.JSONField(default=dict)
    metrics = models.JSONField(default=dict)
    duration = models.FloatField(default=0)
    count = models.IntegerField(default=0)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)

class Assessment(models.Model):
    transaction = models.ForeignKey(Transaction,on_delete=models.CASCADE,related_name='assessments')
    run = models.ForeignKey(DetectionRun,on_delete=models.CASCADE)
    forest = models.FloatField()
    lof = models.FloatField()
    cluster = models.IntegerField()
    risk = models.IntegerField()
    decision = models.CharField(max_length=20)
    reasons = models.JSONField(default=list)
    split = models.CharField(max_length=20)
    explanation = models.JSONField(default=dict)

class FraudCase(models.Model):
    transaction = models.OneToOneField(Transaction,on_delete=models.CASCADE)
    status = models.CharField(max_length=20,default='Open')
    outcome = models.CharField(max_length=30,blank=True)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    updated = models.DateTimeField(auto_now=True)
    closed_at = models.IntegerField(null=True, blank=True)
    demo_history = models.BooleanField(default=False)

    @property
    def closed_date(self):
        return SIMULATION_START + timedelta(seconds=self.closed_at) if self.closed_at is not None else None

class CaseNote(models.Model):
    case = models.ForeignKey(FraudCase,on_delete=models.CASCADE,related_name='notes')
    author = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

class AuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
    action = models.CharField(max_length=100)
    target = models.CharField(max_length=100)
    reason = models.TextField()
    before = models.CharField(max_length=100,blank=True)
    after = models.CharField(max_length=100,blank=True)
    created = models.DateTimeField(auto_now_add=True)


class AnalysisJob(models.Model):
    """A durable local queue, processed by one background worker."""
    kind = models.CharField(max_length=12, choices=[('single', 'Tranzacție'), ('replay', 'Set de date')])
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=12, default='queued', db_index=True,
                              choices=[('queued', 'În așteptare'), ('running', 'În analiză'),
                                       ('completed', 'Finalizată'), ('failed', 'Eșuată')])
    created = models.DateTimeField(auto_now_add=True)
    started = models.DateTimeField(null=True)
    finished = models.DateTimeField(null=True)
    error = models.TextField(blank=True)
    parameters = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['transaction'], condition=models.Q(kind='single'),
                                                name='one_analysis_job_per_transfer')]


class DemoPlayback(models.Model):
    """Single local presentation clock. Future rows remain outside analyst queries."""
    status = models.CharField(max_length=12, default='paused')
    interval = models.PositiveIntegerField(default=3)
    last_release = models.DateTimeField(null=True)
    heartbeat = models.DateTimeField(null=True)
    released = models.PositiveIntegerField(default=0)
