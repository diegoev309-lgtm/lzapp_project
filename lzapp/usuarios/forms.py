from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
import re
from dashboard.models import Perfil


class RegistroForm(UserCreationForm):

    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su usuario'
        })
    )

    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su correo'
        })
    )

    telefono = forms.CharField(
        label="Teléfono",
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su teléfono'
        })
    )

    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña'
        })
    )

    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme su contraseña'
        })
    )

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'telefono',
            'password1',
            'password2'
        ]

    import re

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
        email = self.cleaned_data.get("email")

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")

        return email


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