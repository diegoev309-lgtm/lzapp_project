from django.shortcuts import render,redirect
from .logic import Carro
from producto.models import Producto

def agregar_producto(request,producto_id):
    carro=Carro(request)
    identificador=Producto.objects.get(id=producto_id)
    carro.agregar(producto=identificador)
    return redirect("carro")

def eliminar_producto(request,producto_id):
    carro=Carro(request)
    identificador=Producto.objects.get(id=producto_id)
    carro.eliminar(producto=identificador)
    return redirect("carro")

def restar_producto(request,producto_id):
    carro=Carro(request)
    identificador=Producto.objects.get(id=producto_id)
    carro.restar(producto=identificador)
    return redirect("carro")

def limpiar_carro(request):
    carro=Carro(request)
    carro.limpiar_carro()
    return redirect("carro")
    
