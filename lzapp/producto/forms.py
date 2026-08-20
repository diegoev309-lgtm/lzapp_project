import re
from datetime import date
from django import forms
from dashboard.models import Producto

# Solo letras (con tildes/ñ), números y espacios.
NOMBRE_VALIDO_RE = re.compile(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ0-9 ]+$')


class ProductoForm(forms.ModelForm):
    # Se actualiza en clean(); la vista lo usa para avisarle al usuario
    # si el producto quedó oculto en la tienda por falta de datos.
    producto_incompleto = False

    class Meta:
        model = Producto
        fields = '__all__'
        widgets = {
            # Se agrega explícitamente para que el navegador muestre un
            # selector de fecha nativo en vez de un simple input de texto.
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()

        if not nombre:
            raise forms.ValidationError('El nombre es obligatorio.')

        if not NOMBRE_VALIDO_RE.match(nombre):
            raise forms.ValidationError(
                'El nombre solo puede contener letras, números y espacios '
                '(sin caracteres especiales como @, #, %, etc.).'
            )

        # Evita nombres duplicados (comparación insensible a mayúsculas).
        # Se excluye el propio producto cuando se está editando.
        duplicado = Producto.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            duplicado = duplicado.exclude(pk=self.instance.pk)

        if duplicado.exists():
            raise forms.ValidationError('Ya existe un producto con este nombre.')

        return nombre

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')

        if precio is not None and precio <= 0:
            raise forms.ValidationError('El precio debe ser mayor a 0.')

        return precio

    def clean_stock_actual(self):
        stock_actual = self.cleaned_data.get('stock_actual')

        if stock_actual is not None and stock_actual <= 0:
            raise forms.ValidationError('El stock actual no puede ser 0, debe ingresar una cantidad.')

        return stock_actual

    def clean_stock_minimo(self):
        stock_minimo = self.cleaned_data.get('stock_minimo')

        if stock_minimo is not None and stock_minimo <= 0:
            raise forms.ValidationError('El stock mínimo no puede ser 0, debe ingresar una cantidad.')

        return stock_minimo

    def clean_fecha_vencimiento(self):
        fecha_vencimiento = self.cleaned_data.get('fecha_vencimiento')

        if fecha_vencimiento and fecha_vencimiento < date.today():
            raise forms.ValidationError(
                'La fecha de vencimiento no puede ser una fecha pasada.'
            )

        return fecha_vencimiento

    def clean(self):
        cleaned_data = super().clean()

        # Campos que deben estar completos para que el producto se
        # muestre en la tienda a los clientes.
        imagen = cleaned_data.get('imagen')
        descripcion = cleaned_data.get('descripcion')
        stock_actual = cleaned_data.get('stock_actual')
        stock_minimo = cleaned_data.get('stock_minimo')
        precio = cleaned_data.get('precio')

        campos_completos = bool(imagen) and bool(descripcion) and bool(stock_actual) \
            and bool(stock_minimo) and bool(precio)

        # Guardamos el resultado para que la vista pueda avisarle al
        # usuario por qué el producto no quedó visible en la tienda.
        self.producto_incompleto = not campos_completos

        if not campos_completos:
            # No importa lo que haya marcado el checkbox de "disponibilidad":
            # un producto incompleto nunca debe mostrarse en la tienda.
            cleaned_data['disponibilidad'] = False

        return cleaned_data

class ImportarProductosForm(forms.Form):
    archivo = forms.FileField(
        label='Selecciona el archivo Excel (.xlsx)',
        widget=forms.ClearableFileInput(attrs={'accept': '.xlsx,.xls'})
    )