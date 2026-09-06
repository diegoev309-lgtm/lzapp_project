from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone

from dashboard.models import SesionActiva
from .utils import obtener_configuracion, obtener_ip_cliente


class SeguridadSesionMiddleware:
    #"""
    #IMPORTANTE: debe ir AL FINAL de MIDDLEWARE (después de MessageMiddleware
    #y AuthenticationMiddleware) — necesita request.user y request._messages
    #ya listos; si fuera antes, messages.error() explota con MessageFailure.
    #
    #Por cada request autenticado: refresca la fila SesionActiva (IP/UA/
    #última actividad) y, si el usuario es staff/superuser y la detección de
    #inactividad está activa, desloguea automáticamente cuando ya pasó
    #demasiado tiempo desde la última actividad registrada. Los clientes del
    #storefront (no staff) nunca se desloguean por esta vía.
    #"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            respuesta_bloqueo = self._procesar(request)
            if respuesta_bloqueo is not None:
                return respuesta_bloqueo
        return self.get_response(request)

    def _procesar(self, request):
        session_key = request.session.session_key
        if not session_key:
            return None

        sesion, creada = SesionActiva.objects.get_or_create(
            session_key=session_key,
            defaults={
                'usuario': request.user,
                'direccion_ip': obtener_ip_cliente(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
            },
        )

        if not creada:
            ultima_actividad_previa = sesion.ultima_actividad
            es_staff = request.user.is_staff or request.user.is_superuser

            if es_staff:
                config = obtener_configuracion()
                if config.deteccion_inactividad_activa:
                    limite = timezone.now() - timedelta(minutes=config.minutos_inactividad)
                    if ultima_actividad_previa < limite:
                        logout(request)  # dispara user_logged_out -> borra esta misma fila
                        messages.error(request, 'Tu sesión se cerró por inactividad.')
                        return redirect('login')

        # .update() en vez de .save(update_fields=...): si la fila fue
        # borrada entre el get_or_create de arriba y este punto (logout en
        # otra pestaña, el comando limpiar_sesiones_inactivas, etc.), un
        # save() explota con NotUpdated -- un update() sobre 0 filas
        # simplemente no hace nada, que es lo correcto acá.
        SesionActiva.objects.filter(pk=sesion.pk).update(
            direccion_ip=obtener_ip_cliente(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            ultima_actividad=timezone.now(),
        )
        return None
