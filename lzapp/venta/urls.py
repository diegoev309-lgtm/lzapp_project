from django.urls import path
from . import views

urlpatterns = [
    path('', views.panel_ventas, name='panel_ventas'),
    path('detalle-dia/', views.detalle_dia_ventas, name='detalle_dia_ventas'),
]