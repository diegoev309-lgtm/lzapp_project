from django.urls import path
from . import views

app_name="carro"

urlpatterns = [
    path('agregar/<int:producto_id>/',views.agregar_producto,name="agregar"),
    path('eliminar/<int:producto_id>/',views.eliminar_producto,name="eliminar"),
    path('restar/<int:producto_id>/',views.restar_producto,name="restar"),
    path('limpiar',views.limpiar_carro,name="limpiar"),
    path("pagar/", views.crear_preferencia, name="crear_preferencia"),
    path("pago-exitoso/", views.pago_exitoso, name="pago_exitoso"),
    path("pago-fallido/", views.pago_fallido, name="pago_fallido"),
    path("pago-pendiente/", views.pago_pendiente, name="pago_pendiente"),
    path("webhook-mp/", views.webhook_mercadopago, name="webhook_mp"),
]