import threading
import os
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from email.mime.image import MIMEImage


def _enviar_email_bienvenida(usuario_id):
    try:
        usuario = User.objects.get(id=usuario_id)
    except User.DoesNotExist:
        return
    html_content = render_to_string('emails/bienvenida.html', {'nombre': usuario.username})
    email = EmailMultiAlternatives(
        subject='¡Bienvenido a LzApp!',
        body=f'Hola {usuario.username}, gracias por registrarte en LzApp.',
        from_email='no-reply@lzapp.com',
        to=[usuario.email],
    )
    email.attach_alternative(html_content, "text/html")
    ruta_logo = os.path.join(settings.BASE_DIR, 'usuarios', 'static', 'usuarios', 'img', 'logolacz.webp')
    try:
        with open(ruta_logo, 'rb') as f:
            logo = MIMEImage(f.read())
            logo.add_header('Content-ID', '<logo_lacz>')
            email.attach(logo)
    except FileNotFoundError:
        print(f"[AVISO] No se encontró el logo en: {ruta_logo}")
    email.send(fail_silently=False)


def enviar_email_bienvenida_async(usuario_id):
    hilo = threading.Thread(target=_enviar_email_bienvenida, args=(usuario_id,))
    hilo.daemon = True
    hilo.start()


def _enviar_email_recuperacion(usuario_id, dominio, protocolo='https'):
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

    ruta_logo = os.path.join(settings.BASE_DIR, 'usuarios', 'static', 'usuarios', 'img', 'logolacz.webp')
    try:
        with open(ruta_logo, 'rb') as f:
            logo = MIMEImage(f.read())
            logo.add_header('Content-ID', '<logo_lacz>')
            email.attach(logo)
    except FileNotFoundError:
        print(f"[AVISO] No se encontró el logo en: {ruta_logo}")

    email.send(fail_silently=False)


def enviar_email_recuperacion_async(usuario_id, dominio, protocolo='https'):
    hilo = threading.Thread(
        target=_enviar_email_recuperacion,
        args=(usuario_id, dominio, protocolo)
    )
    hilo.daemon = True
    hilo.start()