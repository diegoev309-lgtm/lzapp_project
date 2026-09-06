"""Paginación compartida por todos los módulos del dashboard.

Antes cada plantilla recorría `paginator.page_range` entera, así que en
Usuarios (que tiene muchos registros) salía una tira de decenas de
números que no cabía en pantalla. Acá se calcula una ventana alrededor de
la página actual y se ofrece un selector de cuántas filas mostrar.
"""

# Cuántas filas puede pedir el usuario por tabla.
OPCIONES_POR_PAGINA = [10, 25, 50, 100]
POR_PAGINA_DEFECTO = 10

# Páginas visibles a cada lado de la actual.
VENTANA = 2


def leer_por_pagina(request, defecto=POR_PAGINA_DEFECTO, param='por_pagina'):
    """Cuántas filas mostrar, leído de la URL y acotado a la lista.

    Se valida contra las opciones fijas y no contra un rango: si no, un
    ?por_pagina=100000 en la URL obligaría a la base a traer la tabla
    completa de una.

    `param` se cambia cuando hay dos tablas paginadas en la misma pantalla
    (Descuentos tiene productos y campañas), para que el selector de una
    no redimensione la otra.
    """
    try:
        valor = int(request.GET.get(param, defecto))
    except (TypeError, ValueError):
        return defecto
    return valor if valor in OPCIONES_POR_PAGINA else defecto


def ventana_de_paginas(actual, total, ventana=VENTANA):
    """Números de página a mostrar alrededor de la actual.

    Mantiene el ancho de la ventana aunque la página actual esté en un
    extremo: si estás en la 1 de 20, se ven 1-5 y no solo 1-3.
    """
    if total <= 0:
        return []

    ancho = ventana * 2 + 1
    inicio = max(actual - ventana, 1)
    fin = min(inicio + ancho - 1, total)
    inicio = max(min(inicio, fin - ancho + 1), 1)

    return list(range(inicio, fin + 1))
