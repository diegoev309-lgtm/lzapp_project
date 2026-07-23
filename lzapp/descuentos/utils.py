from decimal import Decimal
from django.utils import timezone
from dashboard.models import Descuento


def obtener_descuento_activo(producto):
    """
    Devuelve el descuento activo del producto o None.
    """
    ahora = timezone.now()
    return (producto.descuentos.filter(activo=True,fecha_inicio__lte=ahora)
        .exclude(fecha_fin__lt=ahora)
        .order_by("-fecha_inicio")
        .first()
    )


def calcular_precio_descuento(producto):
    descuento = obtener_descuento_activo(producto)
    if not descuento:
        return producto.precio
    return producto.precio * (Decimal(100 - descuento.porcentaje) / Decimal(100))


def desactivar_descuentos(producto):
    producto.descuentos.filter(activo=True).update(activo=False)


def dias_sin_movimiento(producto):
    if not producto.fecha_ultimo_movimiento_stock:
        return 0
    return (timezone.now() -producto.fecha_ultimo_movimiento_stock).days


def ratio_stock(producto):

    if producto.stock_minimo == 0:
        return float(producto.stock_actual)
    return producto.stock_actual / producto.stock_minimo