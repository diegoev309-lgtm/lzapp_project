from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from dashboard.models import Venta
from usuarios.utils import adjuntar_logo_lacz


def _construir_items_email(venta):
    base_url = settings.SITE_URL.strip()
    items = []
    for detalle in venta.detalles.select_related('producto'):
        producto = detalle.producto
        items.append({
            'nombre': producto.nombre,
            'cantidad': detalle.cantidad,
            'precio_unitario': detalle.precio_unitario,
            'subtotal': detalle.subtotal,
            'imagen_url': f"{base_url}{producto.imagen.url}" if producto.imagen else None,
        })
    return items


def enviar_email_compra(venta_id):
    #"""
    #Envío síncrono a propósito (ver la misma nota en usuarios/utils.py):
    #un hilo en segundo plano se perdía en silencio cuando el autoreloader
    #de `runserver` reiniciaba el proceso a mitad del envío. El webhook de
    #Mercado Pago no lo espera un usuario mirando la pantalla, así que
    #bloquear aquí no afecta la experiencia de compra.
    #"""
    try:
        venta = Venta.objects.select_related('usuario').get(id=venta_id)
    except Venta.DoesNotExist:
        return

    if not venta.usuario.email:
        return

    html_content = render_to_string('emails/compra_confirmada.html', {
        'nombre': venta.usuario.username,
        'venta': venta,
        'items': _construir_items_email(venta),
    })

    email = EmailMultiAlternatives(
        subject='Tu compra en LzApp fue confirmada',
        body=f'Hola {venta.usuario.username}, tu pago fue aprobado. Total: ${venta.total}.',
        from_email='no-reply@lzapp.com',
        to=[venta.usuario.email],
    )
    email.attach_alternative(html_content, "text/html")
    adjuntar_logo_lacz(email)
    email.send(fail_silently=False)
