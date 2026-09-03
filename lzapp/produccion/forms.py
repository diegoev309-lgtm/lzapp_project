from datetime import date
from django import forms
from dashboard.models import Produccion

CANTIDAD_MAXIMA = 100_000
OBSERVACION_MAX_CARACTERES = 2000


class ProduccionForm(forms.ModelForm):
    class Meta:
        model = Produccion
        fields = ['producto', 'cantidad_producida', 'fecha_vencimiento', 'observacion']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_producida': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 1, 'max': CANTIDAD_MAXIMA, 'placeholder': 'Ingrese la cantidad producida'}),
            'fecha_vencimiento': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}),
            'observacion': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4, 'maxlength': OBSERVACION_MAX_CARACTERES, 'placeholder': 'Observaciones de la producción'}),
        }

    def clean_cantidad_producida(self):
        cantidad = self.cleaned_data.get('cantidad_producida')

        if cantidad is not None and cantidad <= 0:
            raise forms.ValidationError('La cantidad producida debe ser mayor a 0.')

        if cantidad is not None and cantidad > CANTIDAD_MAXIMA:
            raise forms.ValidationError(f'La cantidad producida no puede superar {CANTIDAD_MAXIMA:,}'.replace(',', '.') + ' unidades.')

        return cantidad

    def clean_fecha_vencimiento(self):
        fecha_vencimiento = self.cleaned_data.get('fecha_vencimiento')

        if fecha_vencimiento and fecha_vencimiento < date.today():
            raise forms.ValidationError('La fecha de vencimiento no puede ser una fecha pasada.')

        return fecha_vencimiento

    def clean_observacion(self):
        observacion = self.cleaned_data.get('observacion', '')

        if observacion and len(observacion) > OBSERVACION_MAX_CARACTERES:
            raise forms.ValidationError(
                f'La observación no puede superar {OBSERVACION_MAX_CARACTERES} caracteres.'
            )

        return observacion

class ImportarProduccionForm(forms.Form):
    archivo = forms.FileField(
        label='Selecciona el archivo Excel (.xlsx)',
        widget=forms.ClearableFileInput(attrs={'accept': '.xlsx,.xls', 'id': 'id_archivo_produccion'})
    )
