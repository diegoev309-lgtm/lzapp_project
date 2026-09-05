from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()

@register.filter
def get_item(diccionario, clave):
    """
    Lookup de diccionario por clave dentro de un template (ej. para leer
    la cantidad de un producto puntual dentro de carrito_cantidades, que
    llega keyeado como string porque así se guarda el carrito en sesión).
    """
    if not diccionario:
        return None
    return diccionario.get(str(clave))

@register.filter
def mul(valor, factor):
    """
    Multiplica dos valores dentro de un template (ej. precio unitario x
    cantidad, para mostrar el subtotal de una fila del carrito).
    """
    try:
        return Decimal(str(valor)) * Decimal(str(factor))
    except (InvalidOperation, ValueError, TypeError):
        return 0

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