from django.shortcuts import render,redirect
from .logic import Carro
from dashboard.models import Producto

def agregar_producto(request,producto_id):
    carro=Carro(request)
    identificador=Producto.objects.get(id=producto_id)
    carro.agregar(producto=identificador)
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
    


import mercadopago
from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)


def crear_preferencia(request):
    usuario_id = request.session.get('usuario_id')
    carrito = request.session.get('carrito', {})

    if not carrito:
        return HttpResponseBadRequest("El carrito está vacío")

    items = []
    for producto_id, item in carrito.items():
        items.append({
            "id": str(producto_id),
            "title": item["nombre"],
            "quantity": int(item["cantidad"]),
            "unit_price": float(item["precio"]),
            "currency_id": "COP",
        })

    preference_data = {
        "items": items,
        "back_urls": {
            "success": f"{settings.SITE_URL}/carrito/pago-exitoso/",
            "failure": f"{settings.SITE_URL}/carrito/pago-fallido/",
            "pending": f"{settings.SITE_URL}/carrito/pago-pendiente/",
        },
        "auto_return": "approved",
        "notification_url": f"{settings.SITE_URL}/carrito/webhook-mp/",
        "external_reference": str(usuario_id),
        "statement_descriptor": "LACTEOS ZULIANOS",
    }

    preference_response = sdk.preference().create(preference_data)
    preference = preference_response["response"]

    # Guardamos el id de preferencia en sesión por si necesitas rastrearlo
    request.session['mp_preference_id'] = preference["id"]

    return redirect(preference["init_point"])


def pago_exitoso(request):
    payment_id = request.GET.get("payment_id")
    status = request.GET.get("status")
    # Aquí puedes marcar el pedido como pagado, limpiar el carrito, etc.
    request.session['carrito'] = {}
    return render(request, "carrito/pago_exitoso.html", {"payment_id": payment_id, "status": status})


def pago_fallido(request):
    return render(request, "carrito/pago_fallido.html")


def pago_pendiente(request):
    return render(request, "carrito/pago_pendiente.html")


@csrf_exempt
@require_POST
def webhook_mercadopago(request):
    topic = request.GET.get("topic") or request.GET.get("type")
    resource_id = request.GET.get("id") or request.GET.get("data.id")

    if topic == "payment":
        payment_info = sdk.payment().get(resource_id)
        payment = payment_info["response"]

        status = payment.get("status")  # approved, rejected, pending, in_process
        external_reference = payment.get("external_reference")  # tu usuario_id

        # Aquí actualizas tu modelo de Pedido/Orden en base a status
        # Ejemplo:
        # pedido = Pedido.objects.get(usuario_id=external_reference, estado='pendiente')
        # pedido.estado = status
        # pedido.mp_payment_id = payment["id"]
        # pedido.save()

    return JsonResponse({"received": True})