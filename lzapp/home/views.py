from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from django.templatetags.static import static
from dashboard.models import Producto

def buscar_productos_ajax(request):
    """Devuelve productos filtrados en JSON para reconstruir el grid de tarjetas en vivo."""
    query = request.GET.get('q', '').strip()
    productos = Producto.objects.filter(disponibilidad=True)

    if query:
        productos = productos.filter(Q(nombre__icontains=query) | Q(descripcion__icontains=query))

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

def main(request):
    productos = Producto.objects.filter(disponibilidad=True)
    query = request.GET.get("q", "")
    return render(request,"masterpage.html",{"productos":productos,"query":query})

def user(request):
    productos = Producto.objects.filter(disponibilidad=True)
    return render(request, "users.html", {"productos": productos})

def client(request):
    productos = Producto.objects.filter(disponibilidad=True)
    return render(request, "clients.html", {"productos": productos})

def carro(request):
    productos, query = buscar_productos_ajax(request)
    return render(request, "carrito_compras.html", {"productos": productos, "query": query})

#def home(request):
#    query = request.GET.get('q', '')
#    productos_qs = Producto.objects.filter(disponibilidad=True)
#    if query:
#        productos_qs = productos_qs.filter(nombre__icontains=query)
#    todos = list(Producto.objects.filter(disponibilidad=True).prefetch_related('descuentos'))
#
#    # Prioridad: 1º los que YA tienen descuento vigente (real, de tu sistema),
#    # 2º entre esos, el que tiene más stock sobrante primero.
#    todos_ordenados = sorted(todos,key=lambda p: (p.descuento_vigente is None, -p.ratio_stock))
#    productos_oferta = todos_ordenados[:3]
#
#    return render(request, 'masterpage.html', {'productos': productos_qs,'query': query,'productos_oferta': productos_oferta,})