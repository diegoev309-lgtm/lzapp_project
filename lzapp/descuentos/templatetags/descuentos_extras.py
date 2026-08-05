from django import template

register = template.Library()


@register.filter
def dict_get(diccionario, clave):
    """
    Django no permite acceso a diccionarios por variable dentro del
    template (solo por clave literal). Este filtro permite hacer
    `{{ mi_diccionario|dict_get:mi_variable }}`.
    Se usa en formdes.html para cruzar cada checkbox de producto con
    su badge de vencimiento (productos_badges).
    """
    if not diccionario:
        return None
    return diccionario.get(str(clave))