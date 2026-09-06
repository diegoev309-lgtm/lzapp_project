from django.urls import path
from . import views

urlpatterns = [
    path('Pedidos', views.Pedidos, name="Pedidos"),
    path('pedido_tiempo', views.api_pedidos_tiempo_real, name="pedido_tiempo"),
    path('mis-entregas', views.mis_entregas, name="mis_entregas"),
    path('mis-entregas-tiempo', views.mis_entregas_tiempo_real, name="mis_entregas_tiempo_real"),
    path('actualizar-ubicacion', views.actualizar_ubicacion_repartidor, name="actualizar_ubicacion_repartidor"),
    path('estado-reparto', views.cambiar_estado_reparto, name="cambiar_estado_reparto"),
    path('vehiculo', views.actualizar_vehiculo, name="actualizar_vehiculo"),
    path('mi-vehiculo', views.mi_vehiculo, name="mi_vehiculo"),
    path('cancelar/<int:pedido_id>/', views.cancelar_pedido, name="cancelar_pedido"),
    path('confirmar-entrega/<int:pedido_id>/', views.confirmar_entrega_pedido, name="confirmar_entrega_pedido"),
    path('incidencia/<int:pedido_id>/', views.reportar_incidencia, name="reportar_incidencia"),
    path('tiempo-preparacion', views.actualizar_tiempo_preparacion, name="actualizar_tiempo_preparacion"),
    path('sugerencia/<int:sugerencia_id>/', views.resolver_sugerencia, name="resolver_sugerencia"),
    path('mi-pedido', views.mi_pedido_seguimiento, name="mi_pedido_seguimiento"),
    path('mi-pedido-tiempo', views.mi_pedido_tiempo_real, name="mi_pedido_tiempo_real"),
]