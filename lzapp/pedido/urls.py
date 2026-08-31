from django.urls import path
from . import views

urlpatterns = [
    path('Pedidos', views.Pedidos, name="Pedidos"),
    path('pedido_tiempo', views.api_pedidos_tiempo_real, name="pedido_tiempo"),
    path('mis-entregas', views.mis_entregas, name="mis_entregas"),
    path('actualizar-ubicacion', views.actualizar_ubicacion_repartidor, name="actualizar_ubicacion_repartidor"),
    path('actualizar-estado/<int:pedido_id>/', views.actualizar_estado_pedido, name="actualizar_estado_pedido"),
]