from django.shortcuts import render
from django.shortcuts import render, redirect

def dview(request):
    return redirect('Inicio_dash')

def Inicio(request):
    return render(request, "Inicio.html")

def Ventas(request):
    return render(request, "ventas.html")

def Pedidos(request):
    return render(request, "pedidos.html")

def Notificaciones(request):
    return render(request, "notificaciones.html")