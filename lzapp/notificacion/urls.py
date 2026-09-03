from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_notificaciones, name='Notificaciones'),
    path('<int:id>/marcar-leida/', views.marcar_notificacion_leida, name='marcar_notificacion_leida'),
    path('marcar-todas-leidas/', views.marcar_todas_leidas, name='marcar_todas_leidas'),

    # Versión cliente (sin gate de staff), usada por la campana del navbar del sitio.
    path('mis-notificaciones/', views.mis_notificaciones, name='mis_notificaciones'),
    path('mis-notificaciones/<int:id>/marcar-leida/', views.marcar_notificacion_leida_cliente, name='marcar_notificacion_leida_cliente'),
    path('mis-notificaciones/marcar-todas-leidas/', views.marcar_todas_leidas_cliente, name='marcar_todas_leidas_cliente'),
]