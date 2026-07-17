from django import forms
from .models import Usuario


class RegistroForm(forms.ModelForm):

    confirmar = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control"
            }
        )
    )

    class Meta:
        model = Usuario

        fields = [
            'nombre',
            'correo',
            'telefono',
            'contraseña'
        ]

        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'correo': forms.EmailInput(attrs={
                'class': 'form-control'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'contraseña': forms.PasswordInput(attrs={
                'class': 'form-control'
            }),
        }

    def clean(self):
        datos = super().clean()

        contraseña = datos.get("contraseña")
        confirmar = datos.get("confirmar")

        if contraseña != confirmar:
            raise forms.ValidationError("Las contraseñas no coinciden.")

        return datos