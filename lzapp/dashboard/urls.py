from django.urls import path
from dashboard.views import dview,Inicio,Producto,Produccion,Ventas,Usuarios,Pedidos,Notificaciones

urlpatterns = [
    path('dview',dview,name="dview"),
    path('Inicio',Inicio,name="Inicio"),
    path('Producto',Producto,name="Producto"),
    path('Produccion',Produccion,name="Produccion"),
    path('Ventas',Ventas,name="Ventas"),
    path('Usuarios',Usuarios,name="Usuarios"),
    path('Pedidos',Pedidos,name="Pedidos"),
    path('Notificaciones',Notificaciones,name="Notificaciones"),
]