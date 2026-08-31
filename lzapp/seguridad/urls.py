from django.urls import path

from . import views

urlpatterns = [
    path('', views.panel_seguridad, name='panel_seguridad'),
    path('guardar/', views.guardar_configuracion_seguridad, name='guardar_configuracion_seguridad'),
    path('sesion/<str:session_key>/cerrar/', views.cerrar_sesion_remota, name='cerrar_sesion_remota'),
]
