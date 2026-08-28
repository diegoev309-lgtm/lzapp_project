from django import forms
from dashboard.models import Produccion

class ProduccionForm(forms.ModelForm):
    class Meta:
        model = Produccion
        fields = ['producto', 'cantidad_producida', 'fecha_vencimiento', 'observacion']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_producida': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Ingrese la cantidad producida'}),
            'fecha_vencimiento': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}),
            'observacion': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Observaciones de la producción'}),
        }

class ImportarProduccionForm(forms.Form):
    archivo = forms.FileField(
        label='Selecciona el archivo Excel (.xlsx)',
        widget=forms.ClearableFileInput(attrs={'accept': '.xlsx,.xls', 'id': 'id_archivo_produccion'})
    )