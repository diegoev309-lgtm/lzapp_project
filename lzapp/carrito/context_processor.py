from django.utils import timezone
from django.utils.dateparse import parse_datetime


def _leer_bandera_ruleta_vigente(request, clave_sesion):
    #"""
    #Lee una bandera de premio de la ruleta diaria (cupon_ruleta /
    #envio_gratis_ruleta) guardada en sesión por
    #descuentos.services.reclamar_premio_dia. Si ya venció, la limpia de
    #la sesión sola (igual que carrito.logic.limpiar_premios_invalidos_del_carrito
    #hace con los premios de campaña) y devuelve None.
    #"""
    dato = request.session.get(clave_sesion)
    if not dato:
        return None
    expiracion = parse_datetime(dato.get('fecha_expiracion', '')) if dato.get('fecha_expiracion') else None
    if not expiracion or timezone.now() > expiracion:
        del request.session[clave_sesion]
        request.session.modified = True
        return None
    return dato


def totalizar_carro(request):
    total = 0
    carro = request.session.get("carro", {})
    for key, value in carro.items():
        total += float(value["precio"]) * value["cantidad"]

    # Cupón de 5% ganado en la ruleta diaria (NO usa DescuentoAsignado,
    # es solo un % ligero en sesión aplicado sobre el total del carrito).
    cupon_ruleta = _leer_bandera_ruleta_vigente(request, 'cupon_ruleta')
    descuento_cupon_ruleta = 0
    if cupon_ruleta:
        descuento_cupon_ruleta = round(total * (cupon_ruleta['porcentaje'] / 100), 2)
        total = round(total - descuento_cupon_ruleta, 2)

    # Envío gratis ganado en la ruleta diaria: el proyecto todavía no
    # calcula ningún costo de envío en ningún lado, así que esto no
    # descuenta nada del total — solo queda disponible como bandera para
    # mostrar un badge tipo "Envío gratis aplicado" en el carrito.
    envio_gratis_ruleta = _leer_bandera_ruleta_vigente(request, 'envio_gratis_ruleta')

    return {
        "totalizar_carro": total,
        "cupon_ruleta_activo": cupon_ruleta,
        "descuento_cupon_ruleta": descuento_cupon_ruleta,
        "envio_gratis_ruleta_activo": envio_gratis_ruleta,
    }

# carrito/context_processors.py
from django.conf import settings

def mercadopago_public_key(request):
    return {"MP_PUBLIC_KEY": settings.MERCADOPAGO_PUBLIC_KEY}