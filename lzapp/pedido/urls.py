from django.urls import path
from . import views

urlpatterns = [
    path('Pedidos', views.Pedidos, name="Pedidos"),
    path('pedido_tiempo', views.api_pedidos_tiempo_real, name="pedido_tiempo"),
    path('mis-entregas', views.mis_entregas, name="mis_entregas"),
    path('mis-entregas-tiempo', views.mis_entregas_tiempo_real, name="mis_entregas_tiempo_real"),
    path('actualizar-ubicacion', views.actualizar_ubicacion_repartidor, name="actualizar_ubicacion_repartidor"),
    path('actualizar-estado/<int:pedido_id>/', views.actualizar_estado_pedido, name="actualizar_estado_pedido"),
    path('mi-pedido', views.mi_pedido_seguimiento, name="mi_pedido_seguimiento"),
    path('mi-pedido-tiempo', views.mi_pedido_tiempo_real, name="mi_pedido_tiempo_real"),
]