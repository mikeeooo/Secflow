from decimal import Decimal

from django import forms

from .models import Account


class SimulationForm(forms.Form):
    sender = forms.ModelChoiceField(label='Cont expeditor', queryset=Account.objects.filter(id__startswith='SIM_').order_by('display_name', 'id'))
    recipient = forms.ModelChoiceField(label='Cont beneficiar', queryset=Account.objects.filter(id__startswith='SIM_').order_by('display_name', 'id'))
    amount = forms.DecimalField(label='Sumă (MDL demo)', min_value=Decimal('.01'), max_value=100000000, max_digits=12, decimal_places=2)
    device = forms.CharField(max_length=80, initial='DEMO_NEW_DEVICE', label='ID dispozitiv (simulat)')
    failed_logins = forms.IntegerField(min_value=0, max_value=20, initial=0, label='Autentificări eșuate')

    def clean(self):
        values = super().clean()
        if values.get('sender') and values.get('sender') == values.get('recipient'):
            raise forms.ValidationError('Alege două conturi diferite.')
        return values
