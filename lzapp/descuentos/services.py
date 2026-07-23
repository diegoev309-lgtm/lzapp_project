from django.utils import timezone
from dashboard.models import Descuento, ReglaDescuentoAutomatico
from .utils import desactivar_descuentos,dias_sin_movimiento,ratio_stock


def aplicar_descuento_manual(producto,porcentaje,fecha_fin=None):
    desactivar_descuentos(producto)
    return Descuento.objects.create(
        producto=producto,
        porcentaje=porcentaje,
        origen="manual",
        fecha_inicio=timezone.now(),
        fecha_fin=fecha_fin,
        activo=True
    )


def quitar_descuento(descuento):
    descuento.activo = False
    descuento.save(update_fields=["activo"])


def crear_regla(datos):
    return ReglaDescuentoAutomatico.objects.create(**datos)


def evaluar_regla(producto, regla):
    condiciones = []
    if regla.dias_sin_movimiento is not None:
        condiciones.append(dias_sin_movimiento(producto)>= regla.dias_sin_movimiento)

    if regla.stock_multiplicador_min is not None:
        condiciones.append(ratio_stock(producto)>= float(regla.stock_multiplicador_min))

    if not condiciones:
        return False

    if regla.tipo_condicion == "AND":
        return all(condiciones)

    return any(condiciones)


def aplicar_descuentos_automaticos(producto):
    reglas = (ReglaDescuentoAutomatico.objects.filter(activa=True).order_by("-prioridad"))
    for regla in reglas:
        if evaluar_regla(producto, regla):
            desactivar_descuentos(producto)
            return Descuento.objects.create(
                producto=producto,
                porcentaje=regla.descuento_porcentaje,
                origen="automatico",
                regla=regla,
                fecha_inicio=timezone.now(),
                activo=True
            )
    return None