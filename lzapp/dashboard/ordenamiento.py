"""Ordenamiento de tablas del dashboard, del lado del servidor.

Se ordena en la base y no en el navegador a propósito: con paginación,
ordenar en el cliente reacomoda solo las filas de la página actual, así
que "ordenar por precio" mostraría el producto más caro *de esta página*
y no el más caro de todos. Eso es peor que no tener orden, porque parece
correcto.

El mapa de columnas permitidas es una lista blanca: sin ella, un
?orden=usuario__password en la URL dejaría ordenar por cualquier campo
alcanzable desde el modelo.
"""


def aplicar_orden(queryset, request, columnas, defecto):
    """Ordena el queryset según ?orden= y ?dir= de la URL.

    columnas: {nombre_publico: campo_orm}. Un nombre público que no esté
              acá se ignora y se usa el de por defecto.
    defecto:  nombre público que se usa cuando no viene nada en la URL.

    Devuelve (queryset_ordenado, columna_activa, direccion).
    """
    columna = request.GET.get('orden', defecto)
    if columna not in columnas:
        columna = defecto

    direccion = request.GET.get('dir', 'asc')
    if direccion not in ('asc', 'desc'):
        direccion = 'asc'

    campo = columnas[columna]
    prefijo = '-' if direccion == 'desc' else ''

    # El segundo criterio ('pk') mantiene el orden estable entre páginas:
    # sin él, dos filas con el mismo valor pueden intercambiarse de una
    # página a otra y una fila aparecería dos veces (o ninguna).
    return queryset.order_by(f'{prefijo}{campo}', 'pk'), columna, direccion
