from django.core.exceptions import ValidationError


def validar_porcentaje(valor):
    if valor < 1:
        raise ValidationError("El descuento mínimo es 1%.")
    if valor > 90:
        raise ValidationError("El descuento máximo permitido es 90%.")
    return valor


def validar_fechas(fecha_inicio, fecha_fin):
    if fecha_fin:
        if fecha_fin <= fecha_inicio:
            raise ValidationError("La fecha final debe ser mayor que la inicial.")


def validar_prioridad(valor):
    if valor < 0:
        raise ValidationError("La prioridad no puede ser negativa.")
    return valor


def validar_regla(regla):
    if (regla.dias_sin_movimiento is None and regla.stock_multiplicador_min is None 
        and regla.dias_antes_vencimiento is None):
        raise ValidationError("Debe definir al menos una condición.")
    return regla