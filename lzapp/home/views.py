from django.shortcuts import render
from producto.models import Producto

def main(request):
    productos = Producto.objects.filter(disponibilidad=True)
    return render(request, "masterpage.html", {"productos": productos})

def user(request):
    productos = Producto.objects.filter(disponibilidad=True)
    return render(request, "users.html", {"productos": productos})

def client(request):
    productos = Producto.objects.filter(disponibilidad=True)
    return render(request, "clients.html", {"productos": productos})

def carro(request):
    productos = Producto.objects.filter(disponibilidad=True)
    return render(request, "carrito_compras.html", {"productos": productos})