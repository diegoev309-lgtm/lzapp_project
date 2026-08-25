"""
Punto único para emitir notificaciones al administrador.

Se usa desde cualquier app del proyecto (producto, venta, produccion, etc.)
en vez de llamar directamente a `django.contrib.messages`. Esta función
hace dos cosas a la vez:

1. Crea el "toast" (mensaje flotante) usando el framework de mensajes de
   Django, que se renderiza en TODAS las páginas del dashboard
   (masterpage_dashboard.html).
2. Guarda la notificación en la base de datos (modelo Notificacion) para
   que quede disponible en el historial del menú de la campana.

Ejemplo de uso, en cualquier views.py:

    from notificacion.utils import notificar

    notificar(request, 'El producto se guardó pero está oculto en la tienda.',
              tipo='warning', url=reverse('listar_productos'))
"""

from django.contrib import messages
from dashboard.models import Notificacion

# El framework de mensajes de Django solo trae 4 niveles por defecto
# (debug/info/success/warning/error); mapeamos nuestros "tipos" a esos tags.
_TAG_A_MESSAGES = {
    'info': messages.INFO,
    'success': messages.SUCCESS,
    'warning': messages.WARNING,
    'error': messages.ERROR,
}


def notificar(request, mensaje, tipo='info', titulo='', url='', usuario=None, guardar_historial=True):
    """
    Emite una notificación: la muestra como toast en la próxima respuesta y
    (por defecto) la guarda en el historial para el menú de la campana.

    - request: necesario para mostrar el toast (puede ser None si solo se
      quiere guardar en el historial, por ejemplo desde una tarea de Celery).
    - tipo: 'info' | 'success' | 'warning' | 'error'.
    - usuario: a quién pertenece la notificación en el historial. Si se
      omite, se usa request.user (o queda general si no hay usuario logueado).
    """
    if request is not None:
        nivel = _TAG_A_MESSAGES.get(tipo, messages.INFO)
        messages.add_message(request, nivel, mensaje)

    if guardar_historial:
        if usuario is None and request is not None and request.user.is_authenticated:
            usuario = request.user

        Notificacion.objects.create(
            usuario=usuario,
            titulo=titulo,
            mensaje=mensaje,
            tipo=tipo if tipo in dict(Notificacion.TIPO_CHOICES) else 'info',
            url=url,
        )