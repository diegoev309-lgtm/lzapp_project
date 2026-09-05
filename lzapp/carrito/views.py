import mercadopago
import json
import os

from django.contrib.auth.models import User
from django.utils import timezone
from urllib.parse import urljoin
from django.urls import reverse
from django.shortcuts import render,redirect
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.db.models import F
from .logic import Carro
from .utils import enviar_email_compra
from .context_processor import totalizar_carro as _totalizar_carro
from dashboard.models import Producto, DescuentoAsignado, Venta, DetalleVenta, Pedido, Perfil
from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.contrib import messages


sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)


def _es_peticion_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _resumen_carro(request, producto_id=None):
    #"""
    #Snapshot del carrito para las respuestas AJAX: cuántos ítems hay en
    #total, el total en plata (mismo cálculo que ya usa el context
    #processor totalizar_carro, incluido el cupón de la ruleta), el
    #estado puntual del producto que se acaba de tocar (o None si ya no
    #está, ej. al restar hasta 0), y el HTML ya renderizado de la lista
    #del widget -- así el cliente solo tiene que reemplazarlo, en vez de
    #tener que reconstruir cada fila a mano en JS (lo que antes hacía que
    #un producto NUEVO nunca apareciera en el carrito sin recargar).
    #"""
    datos = _totalizar_carro(request)
    item = None
    if producto_id is not None:
        entrada = request.session.get('carro', {}).get(str(producto_id))
        if entrada:
            item = {
                'cantidad': entrada['cantidad'],
                'subtotal': round(float(entrada['precio']) * entrada['cantidad'], 2),
            }
    return {
        'cantidad_items': datos['carrito_cantidad_items'],
        'total': datos['totalizar_carro'],
        'item': item,
        'lista_html': render_to_string('carrito/_lista_items.html', {}, request=request),
    }


def agregar_producto(request, producto_id):
    carro = Carro(request)
    identificador = Producto.objects.get(id=producto_id)

    premio = None
    codigo_premio = request.GET.get('premio')

    if codigo_premio and request.user.is_authenticated:
        premio = DescuentoAsignado.objects.filter(
            usuario=request.user,
            codigo=codigo_premio,
            producto=identificador,
            usado=False,
            fecha_expiracion__gte=timezone.now(),
        ).first()

    resultado = carro.agregar(producto=identificador, premio=premio)

    if _es_peticion_ajax(request):
        if not resultado['ok']:
            return JsonResponse({'ok': False, 'error': resultado['error']}, status=409)
        return JsonResponse({'ok': True, **_resumen_carro(request, producto_id)})

    if not resultado["ok"]:
        messages.warning(request, resultado["error"])

    return redirect("carro")


def eliminar_producto(request,producto_id):
    carro=Carro(request)
    identificador=Producto.objects.get(id=producto_id)
    carro.eliminar(producto=identificador)

    if _es_peticion_ajax(request):
        return JsonResponse({'ok': True, **_resumen_carro(request, producto_id)})

    return redirect("carro")


def restar_producto(request,producto_id):
    carro=Carro(request)
    identificador=Producto.objects.get(id=producto_id)
    carro.restar(producto=identificador)

    if _es_peticion_ajax(request):
        return JsonResponse({'ok': True, **_resumen_carro(request, producto_id)})

    return redirect("carro")


def limpiar_carro(request):
    carro=Carro(request)
    carro.limpiar_carro()

    if _es_peticion_ajax(request):
        return JsonResponse({'ok': True, **_resumen_carro(request)})

    return redirect("carro")


def _leer_coords_entrega(request, lat=None, lng=None):
    """Lee lat/lng de la ubicación de entrega que manda el widget del carrito.
    Se guardan en sesión como respaldo: si el navegador vuelve de Mercado Pago
    sin ellas (o el webhook llega primero), igual sabemos a dónde entregar."""
    lat = lat or request.GET.get("lat")
    lng = lng or request.GET.get("lng")

    if lat and lng:
        request.session["entrega_lat"] = lat
        request.session["entrega_lng"] = lng
        return lat, lng

    return request.session.get("entrega_lat"), request.session.get("entrega_lng")


def _construir_preference_data(request, lat=None, lng=None, direccion=None):
    carro = request.session.get("carro", {})

    if not carro:
        return None

    items = []
    codigos_premio = []
    items_comprados = []

    for producto_id, item in carro.items():
        pid = item.get("producto_id", producto_id)
        cantidad = int(item["cantidad"])
        precio = float(item["precio"])

        items.append({
            "id": str(pid),
            "title": item["nombre"],
            "quantity": cantidad,
            "unit_price": precio,
            "currency_id": "COP",
        })

        items_comprados.append({
            "producto_id": int(pid),
            "cantidad": cantidad,
            "precio_unitario": precio,
        })

        if item.get("es_premio") and item.get("codigo_premio"):
            codigos_premio.append(item["codigo_premio"])

    usuario_id = request.session.get("_auth_user_id") or request.session.get("usuario_id")
    request.session["mp_items_comprados"] = list(carro.keys())
    entrega_lat, entrega_lng = _leer_coords_entrega(request, lat, lng)

    carro_url = urljoin(settings.SITE_URL, reverse("carro"))
    notification_url = urljoin(settings.SITE_URL, reverse("carro:webhook_mp"))

    return {
        "items": items,
        #"payer": {
        #    "email": "test_user_123456@testuser.com",
        #    "name": "APRO",
        #    "surname": "TEST",
        #},
        "back_urls": {
            "success": carro_url,
            "failure": carro_url,
            "pending": carro_url,
        },
        "notification_url": notification_url,
        "auto_return": "approved",
        "external_reference": str(usuario_id),
        "statement_descriptor": "LACTEOS ZULIANOS",
        "metadata": {
            "usuario_id": usuario_id,
            "codigos_premio": codigos_premio,  # <-- viaja con la preferencia, no con la sesión
            # Como string JSON: el metadata de MP a veces no preserva bien
            # listas de diccionarios anidados, así que lo serializamos
            # y lo parseamos de vuelta en el webhook.
            "items_comprados_json": json.dumps(items_comprados),
            # Coordenadas y dirección de entrega: viajan con la preferencia
            # para que el webhook pueda dejarlas en el Pedido aunque la
            # sesión del navegador ya no exista cuando Mercado Pago nos
            # notifique.
            "entrega_lat": entrega_lat,
            "entrega_lng": entrega_lng,
            "direccion_entrega": (direccion or '')[:255],
        },
    }


def crear_preferencia(request):
    """Redirect clásico (por si quieres mantenerlo como fallback)."""
    carro = request.session.get("carro", {})
    if not carro:
        return HttpResponseBadRequest("El carrito está vacío")

    errores_stock = _validar_stock_carro(carro)
    if errores_stock:
        messages.error(request, " | ".join(errores_stock))
        return redirect("carro")

    preference_data = _construir_preference_data(request)
    if not preference_data:
        return HttpResponseBadRequest("El carrito está vacío")

    respuesta = sdk.preference().create(preference_data)

    preference = respuesta["response"]
    request.session["mp_preference_id"] = preference["id"]
    return redirect(preference["init_point"])


def crear_preferencia_ajax(request):
    """Devuelve el preference_id para renderizar el Wallet Brick en la página."""
    carro = request.session.get("carro", {})
    if not carro:
        return JsonResponse({"error": "El carrito está vacío"}, status=400)

    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    direccion = request.GET.get('direccion')

    # El JS ya bloquea el botón de pago si faltan, pero se revalida acá
    # también -- no hay que confiar solo en el chequeo del navegador.
    if not lat or not lng:
        return JsonResponse({"error": "Confirma tu ubicación de entrega antes de pagar."}, status=400)

    errores_stock = _validar_stock_carro(carro)
    if errores_stock:
        return JsonResponse({
            "error": "stock_insuficiente",
            "detalle": errores_stock,
        }, status=409)

    preference_data = _construir_preference_data(request, lat=lat, lng=lng, direccion=direccion)
    if not preference_data:
        return JsonResponse({"error": "El carrito está vacío"}, status=400)

    respuesta = sdk.preference().create(preference_data)
    preference = respuesta["response"]

    if "id" not in preference:
        print(">>> ERROR DE MERCADO PAGO:", respuesta)
        return JsonResponse({"error": "No se pudo crear la preferencia", "detalle": preference}, status=502)

    request.session["mp_preference_id"] = preference["id"]
    return JsonResponse({"id": preference["id"]})


def _validar_stock_carro(carro):
    """
    Revisa que haya stock suficiente para cada producto del carrito
    ANTES de crear la preferencia de pago. Devuelve una lista de
    errores (vacía si todo está OK).
    """
    errores = []

    for producto_id, item in carro.items():
        pid = item.get("producto_id", producto_id)
        cantidad_pedida = int(item["cantidad"])

        try:
            producto = Producto.objects.get(pk=pid)
        except Producto.DoesNotExist:
            errores.append(f'"{item["nombre"]}" ya no existe.')
            continue

        if producto.stock_actual < cantidad_pedida:
            if producto.stock_actual == 0:
                errores.append(f'"{producto.nombre}" está agotado.')
            else:
                errores.append(
                    f'Solo quedan {producto.stock_actual} unidades de '
                    f'"{producto.nombre}" (pediste {cantidad_pedida}).'
                )

    return errores


def registrar_pago_aprobado(payment_id, coords_respaldo=None):
    """Registra la venta de un pago aprobado de Mercado Pago.

    Es idempotente (la clave es mp_payment_id), así que da igual quién
    llegue primero: la notificación webhook de MP o el propio navegador
    del cliente al volver de pagar. Eso importa porque el webhook viaja
    por el túnel público (ngrok) y puede no llegar nunca; sin este
    respaldo, una compra pagada no quedaba registrada en ningún lado y
    por lo tanto no generaba Pedido ni llegaba al panel ni al repartidor.

    coords_respaldo: (lat, lng) de la sesión del navegador, por si la
    preferencia se creó sin coordenadas en el metadata.

    Devuelve la Venta (creada o ya existente) o None si no aplica.
    """
    venta_existente = Venta.objects.filter(mp_payment_id=payment_id).first()
    if venta_existente:
        return venta_existente

    payment_info = sdk.payment().get(payment_id)
    payment = payment_info.get("response", {})

    if payment.get("status") != "approved":
        return None

    metadata = payment.get("metadata") or {}
    usuario_id = metadata.get("usuario_id")
    codigos_premio = metadata.get("codigos_premio") or []

    try:
        items_comprados = json.loads(metadata.get("items_comprados_json") or "[]")
    except (TypeError, ValueError):
        items_comprados = []

    usuario = User.objects.filter(pk=usuario_id).first() if usuario_id else None
    if not usuario or not items_comprados:
        return None

    lat = metadata.get("entrega_lat")
    lng = metadata.get("entrega_lng")
    direccion = metadata.get("direccion_entrega")
    if (not lat or not lng) and coords_respaldo:
        lat, lng = coords_respaldo

    with transaction.atomic():
        venta = Venta.objects.create(
            usuario=usuario,
            total=Decimal("0"),
            mp_payment_id=payment_id,
        )

        total_venta = Decimal("0")

        for item in items_comprados:
            try:
                producto = Producto.objects.select_for_update().get(
                    pk=item["producto_id"]
                )
            except Producto.DoesNotExist:
                continue

            cantidad = int(item["cantidad"])
            precio_unitario = Decimal(str(item["precio_unitario"]))
            subtotal = precio_unitario * cantidad

            DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                subtotal=subtotal,
            )

            # F() evita condición de carrera si llegan
            # varias notificaciones casi al mismo tiempo.
            Producto.objects.filter(pk=producto.pk).update(
                stock_actual=F("stock_actual") - cantidad
            )

            total_venta += subtotal

        venta.total = total_venta
        venta.save(update_fields=["total"])

        # El Pedido lo crea la señal post_save de Venta; aquí le dejamos
        # la ubicación de entrega, que es lo que después usa
        # asignar_repartidor_automatico() para elegir repartidor y ruta.
        _guardar_ubicacion_entrega(venta, lat, lng, direccion)

    # Marca cada premio usado como YA UTILIZADO
    if codigos_premio:
        DescuentoAsignado.objects.filter(
            codigo__in=codigos_premio,
            usuario_id=usuario_id,
        ).update(usado=True)

    # Fuera del "with": recién aquí el commit ya quedó confirmado en la
    # base. Envío síncrono a propósito (ver nota en carrito/utils.py).
    enviar_email_compra(venta.id)

    return venta


def _guardar_ubicacion_entrega(venta, lat, lng, direccion=None):
    """Copia las coordenadas y dirección de entrega al Pedido recién creado.

    Si por lo que sea no llegaron con el pago (una preferencia vieja, la
    sesión perdida, el navegador que volvió sin ellas), se cae a la
    ubicación que el cliente ya tiene registrada en su perfil. Un pedido
    sin destino no se le puede asignar a nadie ni dibujar en el mapa, así
    que vale más una ubicación conocida del cliente que ninguna.
    """
    pedido = Pedido.objects.filter(venta=venta).first()
    if not pedido:
        return

    perfil = Perfil.objects.filter(usuario=venta.usuario).first()

    if (not lat or not lng) and perfil:
        lat, lng = perfil.latitud, perfil.longitud

    if not lat or not lng:
        return

    try:
        # replace(',', '.'): en es-co una coordenada puede venir con coma
        # decimal, y Decimal("6,24") revienta.
        pedido.cliente_latitud = Decimal(str(lat).replace(',', '.'))
        pedido.cliente_longitud = Decimal(str(lng).replace(',', '.'))
    except (InvalidOperation, TypeError, ValueError):
        return

    if direccion:
        pedido.direccion_entrega = direccion[:255]
    elif perfil and perfil.direccion:
        pedido.direccion_entrega = perfil.direccion

    pedido.save(update_fields=["cliente_latitud", "cliente_longitud", "direccion_entrega"])


@csrf_exempt
@require_POST
def webhook_mercadopago(request):

    topic = request.GET.get("topic") or request.GET.get("type")
    resource_id = request.GET.get("id") or request.GET.get("data.id")

    if topic == "payment" and resource_id:
        registrar_pago_aprobado(str(resource_id))

    return JsonResponse({"received": True})