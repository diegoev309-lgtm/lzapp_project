from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from django.templatetags.static import static
from dashboard.models import Producto
from descuentos.services import obtener_premio_activo_para_home


def obtener_productos_filtrados(request):
    """
    Lógica de filtrado reutilizable: NO devuelve una respuesta HTTP, solo el
    queryset y el término de búsqueda. La usan tanto el endpoint JSON
    (buscar_productos_ajax) como las vistas que renderizan una página
    completa (main, client, carro), evitando que cada una reimplemente el
    mismo filtro por su cuenta.
    """
    query = request.GET.get('q', '').strip()
    productos = Producto.objects.filter(disponibilidad=True)

    if query:
        productos = productos.filter(Q(nombre__icontains=query) | Q(descripcion__icontains=query))

    return productos, query


def buscar_productos_ajax(request):
    """
    Endpoint JSON puro: lo consume el fetch() del buscador en vivo del
    template. Antes esta función hacía DOS cosas a la vez (filtrar Y
    devolver JSON), y por eso main()/carro() se rompían al intentar
    desempaquetarla como si devolviera (productos, query): un JsonResponse
    no es una tupla.
    """
    productos, query = obtener_productos_filtrados(request)

    resultados = []
    for p in productos:
        resultados.append({
            "id": p.id,
            "nombre": p.nombre,
            "descripcion": p.descripcion or "",
            "precio": str(p.precio),
            "stock_actual": p.stock_actual,
            "stock_minimo": p.stock_minimo,
            "imagen": p.imagen.url if p.imagen else static('img/no-image.png'),
        })

    return JsonResponse({"productos": resultados, "query": query})


def _premio_activo_o_none(request):
    """Evita repetir el chequeo is_authenticated en cada vista del home."""
    if request.user.is_authenticated:
        return obtener_premio_activo_para_home(request.user)
    return None


def main(request):
    productos, query = obtener_productos_filtrados(request)
    context = {
        'productos': productos,
        'query': query,
        'premio_activo': _premio_activo_o_none(request),
    }
    return render(request, "masterpage.html", context)


def user(request):
    productos = Producto.objects.filter(disponibilidad=True)
    return render(request, "users.html", {"productos": productos})


def client(request):
    productos, query = obtener_productos_filtrados(request)
    context = {
        'productos': productos,
        'query': query,
        'premio_activo': _premio_activo_o_none(request),
    }
    return render(request, "clients.html", context)


def carro(request):
    productos, query = obtener_productos_filtrados(request)
    return render(request, "carrito_compras.html", {"productos": productos, "query": query})


def home(request):
    """
    Nota: esta vista queda redundante con client() ahora que ambas hacen
    lo mismo (productos + query + premio_activo, render de clients.html).
    La dejo tal cual para no romper tu urls.py si algo apunta a 'home',
    pero probablemente quieras eliminar una de las dos y quedarte con un
    solo nombre — dime cuál usa tu urls.py como home real y limpio la otra.
    """
    productos, query = obtener_productos_filtrados(request)
    context = {
        'productos': productos,
        'query': query,
        'premio_activo': _premio_activo_o_none(request),
    }
    return render(request, 'clients.html', context)