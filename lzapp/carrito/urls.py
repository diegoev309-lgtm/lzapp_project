from django.urls import path
from . import views

app_name="carro"

urlpatterns = [
    path('agregar/<int:producto_id>/',views.agregar_producto,name="agregar"),
    path('eliminar/<int:producto_id>/',views.eliminar_producto,name="eliminar"),
    path('restar/<int:producto_id>/',views.restar_producto,name="restar"),
    path('limpiar',views.limpiar_carro,name="limpiar"),
    path("preferencia-ajax/", views.crear_preferencia_ajax, name="crear_preferencia_ajax"),
    path("webhook-mp/", views.webhook_mercadopago, name="webhook_mp"),
]