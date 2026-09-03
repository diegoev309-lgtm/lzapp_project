from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from dashboard.models import Perfil

import re

# Códigos de país más relevantes para el negocio (Colombia primero, es el
# default). No se usa una librería como django-phonenumber-field porque el
# proyecto no tiene requirements.txt ni ninguna dependencia declarada hoy.
CODIGOS_PAIS = [
    ('+57', 'Colombia (+57)'),
    ('+1', 'EE. UU. / Canadá (+1)'),
    ('+52', 'México (+52)'),
    ('+58', 'Venezuela (+58)'),
    ('+593', 'Ecuador (+593)'),
    ('+51', 'Perú (+51)'),
    ('+56', 'Chile (+56)'),
    ('+54', 'Argentina (+54)'),
    ('+507', 'Panamá (+507)'),
    ('+506', 'Costa Rica (+506)'),
    ('+55', 'Brasil (+55)'),
    ('+34', 'España (+34)'),
]
CODIGO_PAIS_DEFECTO = '+57'
CODIGOS_PAIS_VALIDOS = {codigo for codigo, _ in CODIGOS_PAIS}

# "+57 3001234567" -> ('+57', '3001234567'). Si el valor guardado no tiene
# código (números guardados antes de este cambio), se asume el default.
_RE_CODIGO_PAIS = re.compile(r'^(\+\d{1,4})\s*(.*)$')


def separar_codigo_pais(valor):
    valor = (valor or '').strip()
    coincidencia = _RE_CODIGO_PAIS.match(valor)
    if coincidencia and coincidencia.group(1) in CODIGOS_PAIS_VALIDOS:
        return coincidencia.group(1), coincidencia.group(2).strip()
    return CODIGO_PAIS_DEFECTO, valor


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
        telefono = self.cleaned_data.get('telefono', '').strip()

        if not re.match(r'^[0-9+\-\s()]+$', telefono):
            raise forms.ValidationError(
                "El teléfono solo puede contener números, espacios y los símbolos + - ( )."
            )

        if not any(c.isdigit() for c in telefono):
            raise forms.ValidationError(
                "El teléfono debe contener al menos un número."
            )

        return telefono

    def clean(self):
        cleaned_data = super().clean()

        # clean_telefono ya validó que sea solo el número local; acá se le
        # antepone el código de país elegido para guardar un solo valor
        # combinado (ej: "+57 3001234567"), sin agregar una columna nueva.
        codigo_pais = cleaned_data.get('codigo_pais')
        telefono = cleaned_data.get('telefono')
        if codigo_pais and telefono:
            cleaned_data['telefono'] = f'{codigo_pais} {telefono}'

        return cleaned_data


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
        fields = ['telefono', 'direccion']
        widgets = {
            'telefono': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Número sin el código'}
            ),
            'direccion': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
        }

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
        telefono = self.cleaned_data.get('telefono', '').strip()

        if not re.match(r'^[0-9+\-\s()]+$', telefono):
            raise forms.ValidationError(
                "El teléfono solo puede contener números, espacios y los símbolos + - ( )."
            )

        if not any(c.isdigit() for c in telefono):
            raise forms.ValidationError(
                "El teléfono debe contener al menos un número."
            )

        return telefono

    def clean(self):
        cleaned_data = super().clean()

        codigo_pais = cleaned_data.get('codigo_pais')
        telefono = cleaned_data.get('telefono')
        if codigo_pais and telefono:
            cleaned_data['telefono'] = f'{codigo_pais} {telefono}'

        return cleaned_data