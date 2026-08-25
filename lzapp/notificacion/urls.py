from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_notificaciones, name='Notificaciones'),
    path('<int:id>/marcar-leida/', views.marcar_notificacion_leida, name='marcar_notificacion_leida'),
    path('marcar-todas-leidas/', views.marcar_todas_leidas, name='marcar_todas_leidas'),
]