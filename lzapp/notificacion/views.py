from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.timesince import timesince
from django.views.decorators.http import require_POST

from dashboard.models import Notificacion
from seguridad.decorators import vista_dashboard


def _notificaciones_del_usuario(request):
    """Filtro reutilizable: notificaciones generales o del usuario actual."""
    return Q(usuario__isnull=True) | Q(usuario=request.user)


@vista_dashboard
def listar_notificaciones(request):
    """Historial completo de notificaciones (lo que se ve al hacer clic en
    'Ver todas' desde el desplegable de la campana)."""
    notificaciones = Notificacion.objects.filter(
        _notificaciones_del_usuario(request)
    ).order_by('-fecha_creacion')

    paginator = Paginator(notificaciones, 15)
    page = request.GET.get('page')
    notificaciones_pagina = paginator.get_page(page)

    return render(request, 'listn.html', {
        'notificaciones': notificaciones_pagina,
    })


@vista_dashboard
@require_POST
def marcar_notificacion_leida(request, id):
    """AJAX: marca una notificación puntual como leída al hacer clic sobre
    ella en el desplegable de la campana."""
    notificacion = Notificacion.objects.filter(
        _notificaciones_del_usuario(request), id=id
    ).first()

    if notificacion is None:
        return JsonResponse({'ok': False}, status=404)

    if not notificacion.leida:
        notificacion.leida = True
        notificacion.save(update_fields=['leida'])

    return JsonResponse({'ok': True})


@vista_dashboard
@require_POST
def marcar_todas_leidas(request):
    """AJAX: botón 'marcar todas como leídas' del desplegable de la campana."""
    Notificacion.objects.filter(
        _notificaciones_del_usuario(request), leida=False
    ).update(leida=True)
    return JsonResponse({'ok': True})


# =========================================================
# Vistas para el cliente (no staff): mismo historial, pero sin el
# gate de @vista_dashboard, que exige is_staff/is_superuser.
# =========================================================

@login_required
def api_notificaciones(request):
    """Notificaciones recientes del usuario logueado, para que la campana
    se actualice sola sin recargar la página. Sirve para los tres roles:
    cliente, admin y repartidor — cada uno ve solo lo suyo."""
    notificaciones = Notificacion.objects.filter(
        _notificaciones_del_usuario(request)
    ).order_by('-fecha_creacion')

    recientes = [{
        'id': n.id,
        'titulo': n.titulo,
        'mensaje': n.mensaje,
        'tipo': n.tipo,
        'icono': n.icono,
        'url': n.url or '',
        'leida': n.leida,
        'hace': timesince(n.fecha_creacion, timezone.now()),
    } for n in notificaciones[:8]]

    return JsonResponse({
        'no_leidas': notificaciones.filter(leida=False).count(),
        'notificaciones': recientes,
    })


@login_required
def mis_notificaciones(request):
    """Historial completo de notificaciones para el cliente logueado
    (lo que se ve al hacer clic en 'Ver historial completo' desde la
    campana del navbar del sitio, no del panel admin)."""
    notificaciones = Notificacion.objects.filter(
        _notificaciones_del_usuario(request)
    ).order_by('-fecha_creacion')

    paginator = Paginator(notificaciones, 10)
    page = request.GET.get('page')
    notificaciones_pagina = paginator.get_page(page)

    return render(request, 'mis_notificaciones.html', {
        'notificaciones': notificaciones_pagina,
    })


@login_required
@require_POST
def marcar_notificacion_leida_cliente(request, id):
    notificacion = Notificacion.objects.filter(
        _notificaciones_del_usuario(request), id=id
    ).first()

    if notificacion is None:
        return JsonResponse({'ok': False}, status=404)

    if not notificacion.leida:
        notificacion.leida = True
        notificacion.save(update_fields=['leida'])

    return JsonResponse({'ok': True})


@login_required
@require_POST
def marcar_todas_leidas_cliente(request):
    Notificacion.objects.filter(
        _notificaciones_del_usuario(request), leida=False
    ).update(leida=True)
    return JsonResponse({'ok': True})