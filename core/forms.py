from django import forms
from .models import Account
class SimulationForm(forms.Form):
    sender=forms.ModelChoiceField(queryset=Account.objects.filter(id__startswith='SIM_').order_by('id'))
    recipient=forms.ModelChoiceField(queryset=Account.objects.filter(id__startswith='SIM_').order_by('id'))
    amount=forms.DecimalField(min_value=.01,max_value=100000000,max_digits=12,decimal_places=2)
    device=forms.CharField(max_length=80,initial='DEMO_NEW_DEVICE')
    failed_logins=forms.IntegerField(min_value=0,max_value=20,initial=0)
    def clean(self):
        values=super().clean()
        if values.get('sender') and values.get('sender')==values.get('recipient'):
            raise forms.ValidationError('Choose two different accounts.')
        return values
