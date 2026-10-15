from django.contrib import admin
from .models import Account, Transaction, DatasetImport, DetectionRun, Assessment, FraudCase, CaseNote, AuditEvent, AnalysisJob


@admin.register(AnalysisJob)
class AnalysisJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'kind', 'status', 'created', 'finished']
    list_filter = ['status', 'kind']
    readonly_fields = ['created', 'started', 'finished', 'error']
    actions = ['retry_failed']

    @admin.action(description='Reia analizele eșuate')
    def retry_failed(self, request, queryset):
        queryset.filter(status='failed').update(status='queued', started=None, finished=None, error='')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'id', 'risk', 'blocked']
    search_fields = ['display_name', 'id']


for model in [Transaction, DatasetImport, DetectionRun, Assessment, FraudCase, CaseNote, AuditEvent]:
    admin.site.register(model)
