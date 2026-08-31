from django.contrib import messages
from django.contrib.sessions.models import Session
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import vista_dashboard
from .models import SesionActiva
from .utils import describir_dispositivo, obtener_configuracion


@vista_dashboard
def panel_seguridad(request):
    #"""
    #Configuración de detección de inactividad + "mis dispositivos
    #conectados" (estilo WhatsApp): cruza las sesiones de Django todavía
    #vigentes (expire_date en el futuro) con SesionActiva para mostrar
    #IP/dispositivo/última actividad, solo de las sesiones del usuario
    #actual.
    #"""
    configuracion = obtener_configuracion()

    sesiones_vigentes = Session.objects.filter(expire_date__gte=timezone.now())
    claves_vigentes = [
        s.session_key for s in sesiones_vigentes
        if s.get_decoded().get('_auth_user_id') == str(request.user.id)
    ]

    sesion_actual_key = request.session.session_key
    dispositivos = [
        {
            'session_key': sesion.session_key,
            'direccion_ip': sesion.direccion_ip,
            'dispositivo': describir_dispositivo(sesion.user_agent),
            'fecha_inicio': sesion.fecha_inicio,
            'ultima_actividad': sesion.ultima_actividad,
            'es_actual': sesion.session_key == sesion_actual_key,
        }
        for sesion in SesionActiva.objects.filter(session_key__in=claves_vigentes, usuario=request.user)
    ]

    return render(request, 'seguridad.html', {
        'configuracion': configuracion,
        'dispositivos': dispositivos,
    })


@vista_dashboard
@require_POST
def guardar_configuracion_seguridad(request):
    configuracion = obtener_configuracion()
    configuracion.deteccion_inactividad_activa = request.POST.get('activa') == 'on'

    minutos_raw = request.POST.get('minutos', '').strip()
    try:
        minutos = int(minutos_raw)
    except (TypeError, ValueError):
        messages.error(request, 'Los minutos deben ser un número entero.')
        return redirect('panel_seguridad')

    if minutos < 1:
        messages.error(request, 'Los minutos deben ser al menos 1.')
        return redirect('panel_seguridad')

    configuracion.minutos_inactividad = minutos
    configuracion.save(update_fields=[
        'deteccion_inactividad_activa', 'minutos_inactividad', 'fecha_actualizacion',
    ])

    messages.success(request, 'Configuración de seguridad actualizada.')
    return redirect('panel_seguridad')


@vista_dashboard
@require_POST
def cerrar_sesion_remota(request, session_key):
    #"""Cierra una sesión de OTRO dispositivo (nunca la de otro usuario:
    #se valida que la fila le pertenezca a request.user antes de tocar
    #nada)."""
    pertenece_al_usuario = SesionActiva.objects.filter(
        session_key=session_key, usuario=request.user
    ).exists()

    if not pertenece_al_usuario:
        messages.error(request, 'Esa sesión no existe o no te pertenece.')
        return redirect('panel_seguridad')

    Session.objects.filter(session_key=session_key).delete()
    SesionActiva.objects.filter(session_key=session_key).delete()

    messages.success(request, 'Sesión cerrada en ese dispositivo.')
    return redirect('panel_seguridad')
