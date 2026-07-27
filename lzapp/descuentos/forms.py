from django import forms
from dashboard.models import CampanaDescuento


class CampanaDescuentoForm(forms.ModelForm):
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