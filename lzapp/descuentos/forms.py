from decimal import Decimal

from django import forms
from django.db.models import F
from dashboard.models import CampanaDescuento, Producto


class CampanaDescuentoForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Sugerencia visual de vencimiento: los productos que vencen antes
        # aparecen primero en la lista de checkboxes, para que sea más fácil
        # detectar cuáles conviene mover con la campaña. Los que no tienen
        # fecha_vencimiento cargada quedan al final. Esto NO autoselecciona
        # nada, solo cambia el orden en el que se listan.
        self.fields['productos'].queryset = Producto.objects.all().order_by(
            F('fecha_vencimiento').asc(nulls_last=True), 'nombre'
        )

    class Meta:
        model = CampanaDescuento
        fields = [
            'nombre', 'productos', 'porcentaje_descuento',
            'dias_sin_compra', 'cantidad_clientes', 'porcentaje_maximo_clientes',
            'stock_reservado_no_ofertable', 'dias_validez_premio',
            'frecuencia', 'activo', 'fecha_inicio', 'fecha_fin',
        ]
        widgets = {
            'productos': forms.CheckboxSelectMultiple(),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'porcentaje_descuento': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'dias_sin_compra': forms.NumberInput(attrs={'class': 'form-control'}),
            'cantidad_clientes': forms.NumberInput(attrs={'class': 'form-control'}),
            'porcentaje_maximo_clientes': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock_reservado_no_ofertable': forms.NumberInput(attrs={'class': 'form-control'}),
            'dias_validez_premio': forms.NumberInput(attrs={'class': 'form-control'}),
            'frecuencia': forms.Select(attrs={'class': 'form-select'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_porcentaje_descuento(self):
        porcentaje = self.cleaned_data.get('porcentaje_descuento')

        if porcentaje is not None and not (Decimal('0.01') <= porcentaje <= Decimal('100')):
            raise forms.ValidationError('El porcentaje de descuento debe estar entre 0.01% y 100%.')

        return porcentaje

    def clean_porcentaje_maximo_clientes(self):
        porcentaje = self.cleaned_data.get('porcentaje_maximo_clientes')

        if porcentaje is not None and not (Decimal('0') <= porcentaje <= Decimal('100')):
            raise forms.ValidationError('El porcentaje máximo de clientes debe estar entre 0% y 100%.')

        return porcentaje

    def clean(self):
        cleaned_data = super().clean()

        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')

        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise forms.ValidationError('La fecha de fin no puede ser anterior a la fecha de inicio.')

        return cleaned_data