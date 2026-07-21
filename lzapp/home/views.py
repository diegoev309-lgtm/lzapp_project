from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from django.templatetags.static import static
from dashboard.models import Producto

def buscar_productos(request):
    """Filtra productos disponibles según el parámetro ?q= de la URL (para la página completa)."""
    query = request.GET.get('q', '').strip()
    productos = Producto.objects.filter(disponibilidad=True)
    if query:
        productos = productos.filter(Q(nombre__icontains=query) | Q(descripcion__icontains=query))
    return productos, query

def buscar_productos_ajax(request):
    """Devuelve productos en JSON para el buscador en vivo (autocompletado)."""
    query = request.GET.get('q', '').strip()
    resultados = []

    if query:
        productos = Producto.objects.filter(disponibilidad=True).filter(Q(nombre__icontains=query) | Q(descripcion__icontains=query))[:8]  
        # límite para no saturar el dropdown
        for p in productos:
            resultados.append({ "id": p.id,
                                "nombre": p.nombre,
                                "precio": str(p.precio),
                                "imagen": p.imagen.url if p.imagen else static('img/no-image.png'),})
    return JsonResponse({"productos": resultados, "query": query})

def main(request):
    productos, query = buscar_productos(request)
    return render(request, "masterpage.html", {"productos": productos, "query": query})

def user(request):
    productos = Producto.objects.filter(disponibilidad=True)
    return render(request, "users.html", {"productos": productos})

def client(request):
    productos = Producto.objects.filter(disponibilidad=True)
    return render(request, "clients.html", {"productos": productos})

def carro(request):
    productos, query = buscar_productos(request)
    return render(request, "carrito_compras.html", {"productos": productos, "query": query})