from django import forms
from dashboard.models import Producto

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = '__all__'
        widgets = {
            # Se agrega explícitamente para que el navegador muestre un
            # selector de fecha nativo en vez de un simple input de texto.
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}),
        }

class ImportarProductosForm(forms.Form):
    archivo = forms.FileField(
        label='Selecciona el archivo Excel (.xlsx)',
        widget=forms.ClearableFileInput(attrs={'accept': '.xlsx,.xls'})
    )