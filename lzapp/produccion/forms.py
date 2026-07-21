from django import forms
from dashboard.models import Produccion

class ProduccionForm(forms.ModelForm):
    class Meta:
        model = Produccion
        fields = '__all__'
        widgets = {'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_producida': forms.NumberInput
            (attrs={'class': 'form-control','min': 1,'placeholder': 'Ingrese la cantidad producida'}),
            'observacion': forms.Textarea
            (attrs={'class': 'form-control','rows': 4,'placeholder': 'Observaciones de la producción'}),}