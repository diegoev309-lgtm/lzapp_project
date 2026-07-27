from django.urls import path
from . import views

urlpatterns = [
    # Página principal
    path('', views.inicio, name='inicio'),

    # Registro
    path('registro/', views.registro, name='registro'),

    # Inicio de sesión
    path('login/', views.iniciar_sesion, name='login'),

    # Cerrar sesión
    path('logout/', views.cerrar_sesion, name='logout'),

    path('reset/', views.solicitar_reset_password, name='solicitar_reset_password'),
    
    path('reset/<uidb64>/<token>/', views.confirmar_reset_password, name='confirmar_reset_password'),

]