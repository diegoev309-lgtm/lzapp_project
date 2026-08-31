import logging
import os
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from email.mime.image import MIMEImage

logger = logging.getLogger(__name__)

# El logo vive en el static de "home" (es el mismo que usa toda la tienda),
# no en "usuarios" -- antes apuntaba a una ruta que nunca existió, así que
# el logo se omitía en silencio (FileNotFoundError atrapado) en todos los
# correos que lo usan.
RUTA_LOGO = os.path.join(settings.BASE_DIR, 'home', 'static', 'home', 'media', 'logolacz.webp')


def adjuntar_logo_lacz(email):
    try:
        with open(RUTA_LOGO, 'rb') as f:
            logo = MIMEImage(f.read())
            logo.add_header('Content-ID', '<logo_lacz>')
            email.attach(logo)
    except FileNotFoundError:
        logger.warning("No se encontró el logo para el correo en: %s", RUTA_LOGO)


def enviar_email_bienvenida(usuario_id):
    #"""
    #Envío síncrono a propósito: un hilo en segundo plano moría en silencio
    #cada vez que el autoreloader de `runserver` reiniciaba el proceso a
    #mitad del envío (por ejemplo, al guardar cualquier archivo .py),
    #perdiendo el correo sin ningún error visible. El costo de ~1-2s
    #bloqueando el request es imperceptible aquí (formulario de registro).
    #"""
    try:
        usuario = User.objects.get(id=usuario_id)
    except User.DoesNotExist:
        return

    login_url = f"{settings.SITE_URL.strip()}/usuarios/login/"

    html_content = render_to_string('emails/bienvenida.html', {
        'nombre': usuario.username,
        'login_url': login_url,
    })
    email = EmailMultiAlternatives(
        subject='¡Bienvenido a LzApp!',
        body=f'Hola {usuario.username}, gracias por registrarte en LzApp.',
        from_email='no-reply@lzapp.com',
        to=[usuario.email],
    )
    email.attach_alternative(html_content, "text/html")
    adjuntar_logo_lacz(email)
    email.send(fail_silently=False)


def enviar_email_recuperacion(usuario_id, dominio, protocolo='https'):
    #"""Envío síncrono: ver la nota en enviar_email_bienvenida."""
    try:
        usuario = User.objects.get(id=usuario_id)
    except User.DoesNotExist:
        return

    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)
    enlace_reset = (
    f"{protocolo}://{dominio}/usuarios/reset/{uid}/{token}/"
)

    html_content = render_to_string('emails/recuperacion_password.html', {
        'nombre': usuario.username,
        'enlace_reset': enlace_reset,
    })

    email = EmailMultiAlternatives(
        subject='Recupera tu contraseña en LzApp',
        body=f'Hola {usuario.username}, para restablecer tu contraseña visita: {enlace_reset}',
        from_email='no-reply@lzapp.com',
        to=[usuario.email],
    )
    email.attach_alternative(html_content, "text/html")
    adjuntar_logo_lacz(email)
    email.send(fail_silently=False)
