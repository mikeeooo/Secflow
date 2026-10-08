from django.db import models
from django.conf import settings

class Account(models.Model):
    id = models.CharField(primary_key=True,max_length=80)
    blocked = models.BooleanField(default=False)
    risk = models.IntegerField(default=0)
    def __str__(self): return self.pk

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
    risk = models.IntegerField(null=True)
    decision = models.CharField(max_length=20,default='Pending')
    class Meta: ordering = ['-timestamp','id']

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

class FraudCase(models.Model):
    transaction = models.OneToOneField(Transaction,on_delete=models.CASCADE)
    status = models.CharField(max_length=20,default='Open')
    outcome = models.CharField(max_length=30,blank=True)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    updated = models.DateTimeField(auto_now=True)

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
