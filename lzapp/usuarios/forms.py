from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from dashboard.models import Perfil

import re

# Códigos de país más relevantes para el negocio (Colombia primero, es el
# default). No se usa una librería como django-phonenumber-field porque el
# proyecto no tiene requirements.txt ni ninguna dependencia declarada hoy.
#
# La etiqueta es "bandera + código" (ej. "🇨🇴 +57") en vez del nombre del
# país -- el <option> de un <select> nativo solo admite texto plano, pero
# los emoji de bandera SÍ son texto plano (son pares de "regional
# indicator"), así que esto funciona sin íconos ni CSS extra. En Windows
# puede llegar a verse como dos letras en vez de la banderita si el
# navegador/fuente no tiene el glifo, pero la mayoría de Chrome/Edge
# actuales sí lo renderizan bien.
CODIGOS_PAIS = [
    ('+57', '🇨🇴 +57'),
    ('+1', '🇺🇸 +1'),
    ('+52', '🇲🇽 +52'),
    ('+58', '🇻🇪 +58'),
    ('+593', '🇪🇨 +593'),
    ('+51', '🇵🇪 +51'),
    ('+56', '🇨🇱 +56'),
    ('+54', '🇦🇷 +54'),
    ('+507', '🇵🇦 +507'),
    ('+506', '🇨🇷 +506'),
    ('+55', '🇧🇷 +55'),
    ('+34', '🇪🇸 +34'),
]
CODIGO_PAIS_DEFECTO = '+57'
CODIGOS_PAIS_VALIDOS = {codigo for codigo, _ in CODIGOS_PAIS}

# Cantidad de dígitos (mínimo, máximo) del número LOCAL (sin el código de
# país) según el plan de numeración real de cada país. Casi todos son un
# valor fijo; Argentina/Brasil varían un poco porque el número puede
# llevar o no el "9" célular / código de área según la región.
#
# OJO: si cambias esto, actualiza también LONGITUD_POR_PAIS en
# usuarios/static/js/telefono_validacion.js -- son la misma regla
# duplicada a propósito (server autoritativo + feedback en vivo en el
# navegador), no hay una sola fuente de verdad compartida entre Python y
# JS en este proyecto.
LONGITUD_TELEFONO_POR_PAIS = {
    '+57': (10, 10),   # Colombia: celular siempre 10 dígitos
    '+1': (10, 10),    # EE. UU. / Canadá
    '+52': (10, 10),   # México
    '+58': (10, 10),   # Venezuela
    '+593': (9, 9),    # Ecuador
    '+51': (9, 9),     # Perú
    '+56': (9, 9),     # Chile
    '+54': (10, 11),   # Argentina (con/sin el "9" de celular)
    '+507': (7, 8),    # Panamá
    '+506': (8, 8),    # Costa Rica
    '+55': (10, 11),   # Brasil (con/sin el 9no dígito de celular)
    '+34': (9, 9),     # España
}
LONGITUD_TELEFONO_DEFECTO = (7, 15)

# "+57 3001234567" -> ('+57', '3001234567'). Si el valor guardado no tiene
# código (números guardados antes de este cambio), se asume el default.
_RE_CODIGO_PAIS = re.compile(r'^(\+\d{1,4})\s*(.*)$')


def separar_codigo_pais(valor):
    valor = (valor or '').strip()
    coincidencia = _RE_CODIGO_PAIS.match(valor)
    if coincidencia and coincidencia.group(1) in CODIGOS_PAIS_VALIDOS:
        return coincidencia.group(1), coincidencia.group(2).strip()
    return CODIGO_PAIS_DEFECTO, valor


# Validador de teléfono centralizado -- lo usan tanto RegistroForm como
# PerfilUpdateForm (y por herencia, RegistroEmpleadoForm) para no tener
# la misma regla duplicada en dos sitios que se puedan desincronizar.
#
# El código de país ya lo elige el select aparte, así que este campo es
# SOLO el número local: nada de +, espacios, guiones ni paréntesis --
# antes se permitían esos símbolos y por eso "+++" o "3001234567+"
# pasaban la validación con tal de tener algún dígito de sobra.
def validar_telefono(telefono):
    telefono = (telefono or '').strip()

    if not telefono:
        raise forms.ValidationError("Ingresa tu número de teléfono.")

    if not re.match(r'^[0-9]+$', telefono):
        raise forms.ValidationError(
            "El teléfono solo puede contener números -- el código de país ya lo eliges en la lista de al lado."
        )

    return telefono


def validar_y_combinar_telefono(form, cleaned_data):
    """
    Se llama desde clean() de RegistroForm y PerfilUpdateForm: revisa que
    la cantidad de dígitos del número coincida con el país elegido (ej.
    Colombia exige exactamente 10) y, si todo cuadra, arma el valor final
    "+57 3001234567" que se guarda en el modelo. Si no cuadra, adjunta el
    error al campo telefono en vez de dejar pasar un número con la
    longitud equivocada para ese país.
    """
    codigo_pais = cleaned_data.get('codigo_pais')
    telefono = cleaned_data.get('telefono')
    if not codigo_pais or not telefono:
        return cleaned_data

    minimo, maximo = LONGITUD_TELEFONO_POR_PAIS.get(codigo_pais, LONGITUD_TELEFONO_DEFECTO)
    cantidad = len(telefono)

    if cantidad < minimo or cantidad > maximo:
        if minimo == maximo:
            mensaje = f'Para este país, el número debe tener exactamente {minimo} dígitos.'
        else:
            mensaje = f'Para este país, el número debe tener entre {minimo} y {maximo} dígitos.'
        form.add_error('telefono', mensaje)
    else:
        cleaned_data['telefono'] = f'{codigo_pais} {telefono}'

    return cleaned_data


class RegistroForm(UserCreationForm):

    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su usuario',
            'autocomplete': 'username'
        })
    )

    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su correo',
            'autocomplete': 'email'
        })
    )

    codigo_pais = forms.ChoiceField(
        label="",
        choices=CODIGOS_PAIS,
        initial=CODIGO_PAIS_DEFECTO,
        widget=forms.Select(attrs={'class': 'form-control select-codigo-pais'}),
    )

    telefono = forms.CharField(
        label="Teléfono",
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número sin el código',
            'autocomplete': 'tel'
        })
    )

    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña',
            'autocomplete': 'new-password'
        })
    )

    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme su contraseña',
            'autocomplete': 'new-password'
        })
    )

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'codigo_pais',
            'telefono',
            'password1',
            'password2'
        ]

    def clean_username(self):
        username = self.cleaned_data.get("username")

        if len(username) < 6:
            raise forms.ValidationError(
                "El nombre de usuario debe tener al menos 6 caracteres."
            )

        if len(username) > 20:
            raise forms.ValidationError(
                "El nombre de usuario no puede tener más de 20 caracteres."
            )

        if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', username):
            raise forms.ValidationError(
                "Debe comenzar con una letra y solo puede contener letras, números y guiones bajos (_)."
            )

        if not any(c.isdigit() for c in username):
            raise forms.ValidationError(
                "El nombre de usuario debe contener al menos un número."
            )

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "Este nombre de usuario ya está registrado."
            )

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "Ya existe una cuenta registrada con este correo electrónico."
            )

        return email

    def clean_telefono(self):
        return validar_telefono(self.cleaned_data.get('telefono'))

    def clean(self):
        cleaned_data = super().clean()
        return validar_y_combinar_telefono(self, cleaned_data)


class RegistroEmpleadoForm(RegistroForm):
    """
    Reutiliza toda la validación de RegistroForm.
    La diferencia se maneja en la vista:
    al guardar, el PerfilEmple se crea con rol='empleado'.
    """

    class Meta(RegistroForm.Meta):
        model = User
        fields = [
            'username',
            'email',
            'codigo_pais',
            'telefono',
            'password1',
            'password2'
        ]


class LoginForm(AuthenticationForm):

    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su usuario'
        })
    )

    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña'
        })
    )

    error_messages = {
        'invalid_login': 'Usuario o contraseña incorrectos.',
        'inactive': 'Esta cuenta está desactivada.',
    }


class UserUpdateForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control'
            }),
        }

    def clean_username(self):
        username = self.cleaned_data['username']

        if User.objects.exclude(pk=self.instance.pk).filter(
            username=username
        ).exists():
            raise forms.ValidationError(
                "Ese nombre de usuario ya está en uso."
            )

        return username

    def clean_email(self):
        email = self.cleaned_data['email']

        if User.objects.exclude(pk=self.instance.pk).filter(
            email=email
        ).exists():
            raise forms.ValidationError(
                "Ese correo ya está registrado por otro usuario."
            )

        return email


class PerfilUpdateForm(forms.ModelForm):

    codigo_pais = forms.ChoiceField(
        label="",
        choices=CODIGOS_PAIS,
        initial=CODIGO_PAIS_DEFECTO,
        widget=forms.Select(attrs={'class': 'form-control select-codigo-pais'}),
    )

    class Meta:
        model = Perfil
        fields = ['telefono', 'direccion', 'foto']
        widgets = {
            'telefono': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Número sin el código'}
            ),
            'direccion': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'foto': forms.FileInput(
                # style inline además de la clase: si el CSS todavía no
                # cargó (o quedó cacheado viejo), igual no se ve el
                # input crudo de "Elegir archivo" tapando el resto del
                # formulario.
                attrs={'class': 'avatar-input-oculto', 'accept': 'image/*', 'style': 'display:none;'}
            ),
        }

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        if foto and hasattr(foto, 'size') and foto.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La foto no puede pesar más de 5 MB.")
        return foto

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Al editar un perfil ya existente, el teléfono guardado viene
        # combinado ("+57 3001234567") -- se separa para precargar el
        # select y el input de número por separado, no el string completo.
        if self.instance and self.instance.pk and self.instance.telefono:
            codigo, numero = separar_codigo_pais(self.instance.telefono)
            self.fields['codigo_pais'].initial = codigo
            self.initial['telefono'] = numero

    def clean_telefono(self):
        return validar_telefono(self.cleaned_data.get('telefono'))

    def clean(self):
        cleaned_data = super().clean()
        return validar_y_combinar_telefono(self, cleaned_data)