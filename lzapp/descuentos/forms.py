from django import forms
from dashboard.models import Descuento, ReglaDescuentoAutomatico

class DescuentoManualForm(forms.ModelForm):
    class Meta:
        model = Descuento
        fields = ['porcentaje', 'fecha_fin']
        widgets = {
            'porcentaje': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 90}),
            'fecha_fin': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

class ReglaDescuentoAutomaticoForm(forms.ModelForm):
    class Meta:
        model = ReglaDescuentoAutomatico
        fields = [
            'nombre', 'prioridad', 'dias_sin_venderse_min',
            'stock_multiplicador_min', 'dias_antes_vencimiento_max',
            'descuento_porcentaje', 'activa'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
        }