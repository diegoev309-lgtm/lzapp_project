from datetime import date
from django import forms
from dashboard.models import Producto

import re
import hashlib

# Solo letras (con tildes/ñ), números y espacios.
NOMBRE_VALIDO_RE = re.compile(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ0-9 ]+$')

class ProductoForm(forms.ModelForm):
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
        if precio is None:
            return precio

        if precio <= 0:
            raise forms.ValidationError('El precio debe ser mayor a 0.')

        if precio < Decimal('4000.00'):
            raise forms.ValidationError('El precio mínimo permitido es $4.000,00.')

        # Si vino sin decimales (ej. 5000), se normaliza a 5000.00
        return precio.quantize(Decimal('0.01'))

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

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')

        # Solo se valida cuando se sube una imagen NUEVA en esta petición.
        # Si el campo no viene en self.files, es porque no se tocó (edición
        # sin cambiar foto) o simplemente no se subió ninguna — en ambos
        # casos no hay nada que comparar, así que nunca choca con productos
        # sin foto.
        if 'imagen' not in self.files:
            return imagen

        imagen.seek(0)
        nuevo_hash = hashlib.md5(imagen.read()).hexdigest()
        imagen.seek(0)

        duplicado = Producto.objects.filter(imagen_hash=nuevo_hash)
        if self.instance.pk:
            duplicado = duplicado.exclude(pk=self.instance.pk)

        existente = duplicado.first()
        if existente:
            raise forms.ValidationError(
                f'Esta imagen ya se está usando en el producto "{existente.nombre}". Sube una foto distinta.'
            )

        return imagen

    def clean(self):
        cleaned_data = super().clean()

        imagen = cleaned_data.get('imagen')
        descripcion = cleaned_data.get('descripcion')
        stock_actual = cleaned_data.get('stock_actual')
        stock_minimo = cleaned_data.get('stock_minimo')
        precio = cleaned_data.get('precio')

        if not producto_esta_completo(imagen, descripcion, stock_actual, stock_minimo, precio):
            faltantes = []
            if not imagen: faltantes.append('imagen')
            if not descripcion: faltantes.append('descripción')
            if not stock_actual: faltantes.append('stock actual')
            if not stock_minimo: faltantes.append('stock mínimo')
            if not precio: faltantes.append('precio')

            raise forms.ValidationError(
                'No se puede guardar: completa estos campos primero: ' + ', '.join(faltantes) + '.'
            )

        return cleaned_data

class ImportarProductosForm(forms.Form):
    archivo = forms.FileField(
        label='Selecciona el archivo Excel (.xlsx)',
        widget=forms.ClearableFileInput(attrs={'accept': '.xlsx,.xls'})
    )