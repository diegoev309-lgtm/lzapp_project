from django.shortcuts import render
from producto.models import Producto

def main(request):
    productos = Producto.objects.filter(disponibilidad=True)
    return render(request, "masterpage.html", {"productos": productos})

def user(request):
    return render(request, "users.html")

def client(request):
    return render(request, "clients.html")