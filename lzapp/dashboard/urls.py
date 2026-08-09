from django.urls import path,include
from . import views

urlpatterns = [
    path('dview',views.dview,name="dview"),
    path('Inicio',views.Inicio,name="Inicio_dash"),
    path('Pedidos',views.Pedidos,name="Pedidos"),
    path('Notificaciones',views.Notificaciones,name="Notificaciones"),
]