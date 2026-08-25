from dashboard.models import Notificacion


def notificaciones_admin(request):
    """
    Deja disponibles en TODAS las plantillas que extienden
    masterpage_dashboard.html:
      - notificaciones_recientes: últimas notificaciones para el desplegable
        de la campana.
      - notificaciones_no_leidas: cantidad para el puntito rojo del ícono.

    Se muestran las notificaciones generales (usuario=None) junto con las
    propias del usuario logueado.
    """
    if not request.user.is_authenticated:
        return {}

    notificaciones = Notificacion.objects.filter(
        usuario__isnull=True
    ) | Notificacion.objects.filter(usuario=request.user)

    notificaciones = notificaciones.order_by('-fecha_creacion')

    return {
        'notificaciones_recientes': notificaciones[:8],
        'notificaciones_no_leidas': notificaciones.filter(leida=False).count(),
    }