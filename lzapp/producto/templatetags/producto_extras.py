from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()

@register.filter
def cop(valor):
    """
    Formatea un precio en formato colombiano: punto como separador de
    miles y coma para los decimales (ej: 20000 -> "20.000,00").
    """
    if valor is None or valor == '':
        return '0,00'

    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return valor

    formateado = f'{numero:,.2f}'
    formateado = formateado.replace(',', '_').replace('.', ',').replace('_', '.')
    return formateado