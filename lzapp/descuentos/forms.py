from django import forms
from django.utils import timezone
from dashboard.models import Descuento, ReglaDescuentoAutomatico
from .validators import validar_porcentaje,validar_prioridad,validar_fechas,validar_regla


class DescuentoManualForm(forms.ModelForm):

    class Meta:
        model = Descuento
        fields = [
            "porcentaje",
            "fecha_fin",
        ]
        labels = {
            "porcentaje": "Porcentaje de descuento",
            "fecha_fin": "Fecha de finalización",
        }
        help_texts = {
            "fecha_fin": "Opcional. Si no se establece, el descuento permanecerá activo hasta que sea desactivado.",
        }
        widgets = {
            "porcentaje": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
                "max": 90,
                "placeholder": "Ej. 15"
            }),

            "fecha_fin": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local"
            }),
        }

    def clean_porcentaje(self):
        return validar_porcentaje(self.cleaned_data["porcentaje"])

    def clean(self):
        cleaned_data = super().clean()
        validar_fechas(timezone.now(),cleaned_data.get("fecha_fin"))
        return cleaned_data


class ReglaDescuentoAutomaticoForm(forms.ModelForm):

    class Meta:
        model = ReglaDescuentoAutomatico
        fields = [
            "nombre",
            "prioridad",
            "tipo_condicion",
            "stock_multiplicador_min",
            "dias_antes_vencimiento",
            "descuento_porcentaje",
            "activa",
        ]
        labels = {
            "nombre": "Nombre de la regla",
            "prioridad": "Prioridad",
            "tipo_condicion": "Tipo de evaluación",
            "stock_multiplicador_min": "Multiplicador mínimo de stock",
            "dias_antes_vencimiento": "Días antes del vencimiento",
            "descuento_porcentaje": "Porcentaje de descuento",
            "activa": "Regla activa",
        }
        help_texts = {
            "prioridad":
                "Las reglas con mayor prioridad se ejecutan primero.",
            "tipo_condicion":
                "AND = todas las condiciones. OR = cualquiera de ellas.",
            "stock_multiplicador_min":
                "Ejemplo: 2 significa que el stock actual debe ser al menos el doble del stock mínimo.",
            "dias_antes_vencimiento":
                "Disponible cuando el sistema gestione fechas de vencimiento.",
            "descuento_porcentaje":
                "Valor entre 1 y 90.",
        }

        widgets = {

            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej. Exceso de stock"
            }),

            "prioridad": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 0
            }),

            "tipo_condicion": forms.Select(attrs={
                "class": "form-select"
            }),

            "stock_multiplicador_min": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.1",
                "min": "0",
                "placeholder": "Ej. 1.5"
            }),

            "dias_antes_vencimiento": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 0,
                "placeholder": "Futuro módulo"
            }),

            "descuento_porcentaje": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
                "max": 90,
                "placeholder": "Ej. 20"
            }),

            "activa": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }

    def clean_prioridad(self):
        return validar_prioridad(self.cleaned_data["prioridad"])

    def clean_descuento_porcentaje(self):
        return validar_porcentaje(self.cleaned_data["descuento_porcentaje"])

    def clean(self):
        cleaned_data = super().clean()
        validar_regla(cleaned_data)
        return cleaned_data