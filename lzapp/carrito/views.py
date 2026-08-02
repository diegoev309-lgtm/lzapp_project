import mercadopago
import os

from django.utils import timezone
from urllib.parse import urljoin
from django.urls import reverse
from django.shortcuts import render,redirect
from .logic import Carro
from dashboard.models import Producto, DescuentoAsignado
from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

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

    carro.agregar(producto=identificador, premio=premio)
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
    for producto_id, item in carro.items():
        items.append({
            "id": str(item.get("producto_id", producto_id)),
            "title": item["nombre"],
            "quantity": int(item["cantidad"]),
            "unit_price": float(item["precio"]),
            "currency_id": "COP",
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
        },
    }


def crear_preferencia(request):
    """Redirect clásico (por si quieres mantenerlo como fallback)."""
    preference_data = _construir_preference_data(request)
    if not preference_data:
        return HttpResponseBadRequest("El carrito está vacío")

    respuesta = sdk.preference().create(preference_data)

    preference = respuesta["response"]
    request.session["mp_preference_id"] = preference["id"]
    return redirect(preference["init_point"])


def crear_preferencia_ajax(request):
    """Devuelve el preference_id para renderizar el Wallet Brick en la página."""
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


@csrf_exempt
@require_POST
def webhook_mercadopago(request):

    topic = request.GET.get("topic") or request.GET.get("type")
    resource_id = request.GET.get("id") or request.GET.get("data.id")

    if topic == "payment":
        payment_info = sdk.payment().get(resource_id)
        payment = payment_info.get("response", {})

        status = payment.get("status")
        metadata = payment.get("metadata") or {}
        usuario_id = metadata.get("usuario_id")
        codigos_premio = metadata.get("codigos_premio") or []

        if status == "approved":
            # 1) Marca cada premio usado como YA UTILIZADO, para que no se
            #    pueda volver a reclamar ni quede "flotando" en otro carrito.
            if codigos_premio:
                DescuentoAsignado.objects.filter(
                    codigo__in=codigos_premio,
                    usuario_id=usuario_id,
                ).update(usado=True)

            # Aquí también irían: crear el Pedido/Venta real, descontar
            # stock, etc. — dime si quieres que lo armemos también.

    return JsonResponse({"received": True})