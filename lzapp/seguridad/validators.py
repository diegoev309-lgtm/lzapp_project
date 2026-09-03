from decimal import Decimal, InvalidOperation


def leer_entero_acotado(raw, minimo, maximo, nombre='valor'):
    #"""
    #Para vistas que leen un entero directo de request.POST/GET (sin Form):
    #strip -> int() -> rango. Mismo idioma que ya usaba
    #descuentos/views.py:actualizar_premio_ruleta, generalizado para no
    #repetirlo en cada vista. Devuelve (valor, None) si es válido, o
    #(None, mensaje_de_error) si no.
    #"""
    try:
        valor = int(str(raw).strip())
    except (TypeError, ValueError):
        return None, f'{nombre} debe ser un número entero.'

    if not (minimo <= valor <= maximo):
        return None, f'{nombre} debe estar entre {minimo} y {maximo}.'

    return valor, None


def leer_decimal_acotado(raw, minimo, maximo, nombre='valor'):
    #"""Igual que leer_entero_acotado, pero para decimales (ej. coordenadas)."""
    try:
        valor = Decimal(str(raw).strip())
    except (TypeError, ValueError, InvalidOperation):
        return None, f'{nombre} debe ser un número válido.'

    if not (minimo <= valor <= maximo):
        return None, f'{nombre} debe estar entre {minimo} y {maximo}.'

    return valor, None
