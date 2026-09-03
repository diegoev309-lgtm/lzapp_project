from datetime import date
from decimal import Decimal
from django import forms
from dashboard.models import Producto

import re
import hashlib

# Solo letras (con tildes/ñ), números y espacios.
NOMBRE_VALIDO_RE = re.compile(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ0-9 ]+$')

# El precio se ingresa como pesos enteros (sin decimales): los centavos
# se asignan automáticamente en .00 (ver clean_precio). max_digits=8 en
# el modelo = hasta 6 dígitos enteros + 2 decimales.
PRECIO_MAX_DIGITOS_ENTEROS = 6
PRECIO_MAXIMO = 10 ** PRECIO_MAX_DIGITOS_ENTEROS - 1  # 999999

STOCK_MAXIMO = 100_000
DESCRIPCION_MAX_CARACTERES = 2000
IMAGEN_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def producto_esta_completo(imagen, descripcion, stock_actual, stock_minimo, precio):
    """
    Un producto solo se puede guardar como completo (y por lo tanto
    marcarse disponible) si tiene imagen, descripción, stock actual,
    stock mínimo y precio.
    """
    return bool(imagen and descripcion and stock_actual and stock_minimo and precio)


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = '__all__'
        widgets = {
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}),
            'precio': forms.NumberInput(attrs={
                'step': '1',
                'min': '4000',
                'max': str(PRECIO_MAXIMO),
                'maxlength': str(PRECIO_MAX_DIGITOS_ENTEROS),
                'inputmode': 'numeric',
                'placeholder': 'Ej: 20000',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['precio'].help_text = (
            f'Solo pesos enteros (máx. {PRECIO_MAX_DIGITOS_ENTEROS} dígitos, '
            f'hasta ${PRECIO_MAXIMO:,}'.replace(',', '.') + '). '
            'Los centavos (,00) se agregan automáticamente. Moneda: COP.'
        )

        # El stock y la fecha de vencimiento ya no se editan a mano una
        # vez creado el producto: se calculan a partir de los lotes de
        # producción. Se ocultan al editar, pero se siguen enviando (con
        # su valor actual) para que el guardado no falle.
        if self.instance and self.instance.pk:
            for campo in ('stock_actual', 'stock_minimo', 'fecha_vencimiento'):
                self.fields[campo].widget = forms.HiddenInput()
                self.fields[campo].label = ''
                self.fields[campo].help_text = ''

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()

        if not nombre:
            raise forms.ValidationError('El nombre es obligatorio.')

        if not NOMBRE_VALIDO_RE.match(nombre):
            raise forms.ValidationError(
                'El nombre solo puede contener letras, números y espacios '
                '(sin caracteres especiales como @, #, %, etc.).'
            )

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

        # Los decimales no se escriben a mano: se descarta cualquier
        # centavo que haya llegado y se asignan siempre en .00.
        pesos_enteros = int(precio)

        if pesos_enteros > PRECIO_MAXIMO:
            raise forms.ValidationError(
                f'El precio no puede tener más de {PRECIO_MAX_DIGITOS_ENTEROS} dígitos '
                f'(máximo ${PRECIO_MAXIMO:,}'.replace(',', '.') + ').'
            )

        return Decimal(pesos_enteros).quantize(Decimal('0.01'))

    def clean_stock_actual(self):
        stock_actual = self.cleaned_data.get('stock_actual')

        if stock_actual is not None and stock_actual <= 0:
            raise forms.ValidationError('El stock actual no puede ser 0, debe ingresar una cantidad.')

        if stock_actual is not None and stock_actual > STOCK_MAXIMO:
            raise forms.ValidationError(f'El stock actual no puede superar {STOCK_MAXIMO:,}'.replace(',', '.') + ' unidades.')

        return stock_actual

    def clean_stock_minimo(self):
        stock_minimo = self.cleaned_data.get('stock_minimo')

        if stock_minimo is not None and stock_minimo <= 0:
            raise forms.ValidationError('El stock mínimo no puede ser 0, debe ingresar una cantidad.')

        if stock_minimo is not None and stock_minimo > STOCK_MAXIMO:
            raise forms.ValidationError(f'El stock mínimo no puede superar {STOCK_MAXIMO:,}'.replace(',', '.') + ' unidades.')

        return stock_minimo

    def clean_descripcion(self):
        descripcion = self.cleaned_data.get('descripcion', '')

        if descripcion and len(descripcion) > DESCRIPCION_MAX_CARACTERES:
            raise forms.ValidationError(
                f'La descripción no puede superar {DESCRIPCION_MAX_CARACTERES} caracteres.'
            )

        return descripcion

    def clean_fecha_vencimiento(self):
        fecha_vencimiento = self.cleaned_data.get('fecha_vencimiento')

        if fecha_vencimiento and fecha_vencimiento < date.today():
            raise forms.ValidationError(
                'La fecha de vencimiento no puede ser una fecha pasada.'
            )

        return fecha_vencimiento

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')

        if 'imagen' not in self.files:
            return imagen

        if imagen.size > IMAGEN_MAX_BYTES:
            raise forms.ValidationError(
                f'La imagen no puede pesar más de {IMAGEN_MAX_BYTES // (1024 * 1024)} MB.'
            )

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