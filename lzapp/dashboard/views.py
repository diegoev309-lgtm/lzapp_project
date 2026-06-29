from django.shortcuts import render

def dview(resquet):
    return render(resquet, "masterpage_dashboard.html")

def Inicio(request):
    return render(request, "Inicio.html")

def Ventas(request):
    return render(request, "ventas.html")

def Pedidos(request):
    return render(request, "pedidos.html")

def Usuarios(request):
    return render(request, "usuarios.html")

def Notificaciones(request):
    return render(request, "notificaciones.html")