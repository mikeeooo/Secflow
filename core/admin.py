from django.contrib import admin
from .models import Account, Transaction, DatasetImport, DetectionRun, Assessment, FraudCase, CaseNote, AuditEvent
for model in [Account,Transaction,DatasetImport,DetectionRun,Assessment,FraudCase,CaseNote,AuditEvent]: admin.site.register(model)
