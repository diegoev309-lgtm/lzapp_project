# usuarios/tasks.py
import threading
import os
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.models import User
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

    ruta_logo = os.path.join(settings.BASE_DIR, 'usuarios', 'static', 'usuarios', 'img', 'logolacz.png')
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