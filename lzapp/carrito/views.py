import mercadopago
import json
import os

from django.contrib.auth.models import User
from django.utils import timezone
from urllib.parse import urljoin
from django.urls import reverse
from django.shortcuts import render,redirect
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from .logic import Carro
from dashboard.models import Producto, DescuentoAsignado, Venta, DetalleVenta
from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages


sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)


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
    if not resultado["ok"]:
        messages.warning(request, resultado["error"])

    return redirect("carro")


def eliminar_producto(request,producto_id):
    carro=Carro(request)
    identificador=Producto.objects.get(id=producto_id)
    carro.eliminar(producto=identificador)
    return redirect("carro")


def restar_producto(request,producto_id):
    carro=Carro(request)
    identificador=Producto.objects.get(id=producto_id)
    carro.restar(producto=identificador)
    return redirect("carro")


def limpiar_carro(request):
    carro=Carro(request)
    carro.limpiar_carro()
    return redirect("carro")


def _construir_preference_data(request):
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

    errores_stock = _validar_stock_carro(carro)
    if errores_stock:
        return JsonResponse({
            "error": "stock_insuficiente",
            "detalle": errores_stock,
        }, status=409)

    preference_data = _construir_preference_data(request)
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


@csrf_exempt
@require_POST
def webhook_mercadopago(request):

    topic = request.GET.get("topic") or request.GET.get("type")
    resource_id = request.GET.get("id") or request.GET.get("data.id")

    if topic == "payment":
        payment_info = sdk.payment().get(resource_id)
        payment = payment_info.get("response", {})

        status = payment.get("status")
        payment_id = str(payment.get("id") or resource_id)
        metadata = payment.get("metadata") or {}
        usuario_id = metadata.get("usuario_id")
        codigos_premio = metadata.get("codigos_premio") or []

        try:
            items_comprados = json.loads(metadata.get("items_comprados_json") or "[]")
        except (TypeError, ValueError):
            items_comprados = []

        if status == "approved":
            # Idempotencia: si MP reenvía la notificación (pasa seguido),
            # no duplicamos la venta ni descontamos el stock dos veces.
            if not Venta.objects.filter(mp_payment_id=payment_id).exists():
                usuario = User.objects.filter(pk=usuario_id).first() if usuario_id else None

                if usuario and items_comprados:
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

            # Marca cada premio usado como YA UTILIZADO
            if codigos_premio:
                DescuentoAsignado.objects.filter(
                    codigo__in=codigos_premio,
                    usuario_id=usuario_id,
                ).update(usado=True)

    return JsonResponse({"received": True})