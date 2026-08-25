from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from dashboard.models import Notificacion


def _notificaciones_del_usuario(request):
    """Filtro reutilizable: notificaciones generales o del usuario actual."""
    return Q(usuario__isnull=True) | Q(usuario=request.user)


@login_required
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


@login_required
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


@login_required
@require_POST
def marcar_todas_leidas(request):
    """AJAX: botón 'marcar todas como leídas' del desplegable de la campana."""
    Notificacion.objects.filter(
        _notificaciones_del_usuario(request), leida=False
    ).update(leida=True)
    return JsonResponse({'ok': True})