from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone

from .models import SesionActiva
from .utils import obtener_ip_cliente


@receiver(user_logged_in)
def registrar_sesion_activa(sender, request, user, **kwargs):
    #"""
    #login() ya hizo cycle_key()/create() antes de disparar esta señal, así
    #que session_key ya es la clave real guardada en django_session (no hace
    #falta forzar el guardado como con visitantes anónimos).
    #"""
    session_key = request.session.session_key
    if not session_key:
        return

    SesionActiva.objects.update_or_create(
        session_key=session_key,
        defaults={
            'usuario': user,
            'direccion_ip': obtener_ip_cliente(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
            'ultima_actividad': timezone.now(),
        },
    )


@receiver(user_logged_out)
def eliminar_sesion_activa(sender, request, user, **kwargs):
    #"""logout() todavía no llamó a session.flush() cuando se dispara esta
    #señal, así que session_key sigue siendo la clave que hay que borrar."""
    session_key = getattr(request.session, 'session_key', None)
    if session_key:
        SesionActiva.objects.filter(session_key=session_key).delete()
