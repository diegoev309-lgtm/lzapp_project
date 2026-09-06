"""Etiqueta {% paginacion %} para las tablas del dashboard."""
from django import template

from dashboard.paginacion import OPCIONES_POR_PAGINA, ventana_de_paginas

register = template.Library()


def _querystring(request, *quitar):
    """La query actual sin los parámetros indicados.

    Es lo que permite cambiar de página sin perder el buscador ni los
    filtros que el usuario ya había puesto.
    """
    params = request.GET.copy()
    for clave in quitar:
        params.pop(clave, None)
    codificada = params.urlencode()
    return ('&' + codificada) if codificada else ''


@register.inclusion_tag('dashboard/_paginacion.html', takes_context=True)
def paginacion(context, pagina, etiqueta='registros',
               param_pagina='page', param_tam='por_pagina'):
    """Pie de tabla: contador, selector de filas y números de página.

    `pagina` es el objeto Page que devuelve Paginator.get_page().

    param_pagina/param_tam se pasan cuando hay más de una tabla paginada
    en la misma pantalla (Descuentos tiene productos y campañas): si las
    dos usaran ?page=, pasar de página en una movería también la otra.
    """
    request = context['request']
    paginator = pagina.paginator
    total_paginas = paginator.num_pages

    numeros = ventana_de_paginas(pagina.number, total_paginas)

    return {
        'pagina': pagina,
        'numeros': numeros,
        'total_paginas': total_paginas,
        'total_registros': paginator.count,
        'etiqueta': etiqueta,
        'por_pagina': paginator.per_page,
        'opciones': OPCIONES_POR_PAGINA,
        'param_pagina': param_pagina,
        'param_tam': param_tam,
        # Para los enlaces de página: se conserva todo menos la página.
        'qs': _querystring(request, param_pagina),
        # Para el selector de tamaño: además se quita el tamaño y se
        # vuelve a la página 1, porque la que estabas viendo puede ya no
        # existir con el tamaño nuevo.
        'qs_tam': _querystring(request, param_pagina, param_tam),
        'primera': numeros and numeros[0] > 1,
        'ultima': numeros and numeros[-1] < total_paginas,
    }
