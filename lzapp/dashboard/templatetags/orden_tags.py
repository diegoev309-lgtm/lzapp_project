"""Etiqueta {% th_orden %} para las cabeceras ordenables de las tablas."""
from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag(takes_context=True)
def th_orden(context, columna, etiqueta, orden_activo=None, direccion=None):
    """Devuelve el <a> de una cabecera ordenable, con su flecha.

    Al hacer clic en la columna que ya está activa se invierte la
    dirección; en cualquier otra se arranca ascendente, que es lo que
    espera quien la toca por primera vez.

    Se conservan los demás parámetros de la URL (búsqueda, filtros) y se
    vuelve a la página 1: la que estabas viendo pierde sentido cuando
    cambia el orden.
    """
    request = context['request']

    orden_activo = orden_activo or request.GET.get('orden')
    direccion = direccion or request.GET.get('dir', 'asc')

    es_activa = (columna == orden_activo)
    nueva_direccion = 'desc' if (es_activa and direccion == 'asc') else 'asc'

    params = request.GET.copy()
    params.pop('page', None)
    params['orden'] = columna
    params['dir'] = nueva_direccion

    if es_activa:
        icono = 'bi-sort-down' if direccion == 'desc' else 'bi-sort-up'
        clase = 'th-orden activa'
    else:
        icono = 'bi-arrow-down-up'
        clase = 'th-orden'

    # params.urlencode() y no django.utils.http.urlencode(params): sobre un
    # QueryDict, el segundo trata cada valor como lista y produce
    # ?orden=%5B%27nombre%27%5D, o sea orden=['nombre'], que no coincide
    # con ninguna columna y deja el ordenamiento sin efecto.
    return format_html(
        '<a class="{}" href="?{}" title="Ordenar por {}">{}<i class="bi {}"></i></a>',
        clase, params.urlencode(), etiqueta, etiqueta, icono,
    )
