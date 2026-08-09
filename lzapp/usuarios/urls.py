from django.urls import path
from . import views


urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('registro/', views.registro, name='registro'),
    path('login/', views.iniciar_sesion, name='login'),
    path('logout/', views.cerrar_sesion, name='logout'),
    path('reset/', views.solicitar_reset_password, name='solicitar_reset_password'),
    path('reset/<uidb64>/<token>/', views.confirmar_reset_password, name='confirmar_reset_password'),
    path('configuracion/', views.configuracion, name='configuracion'),
    path('Usuario',views.Usuario,name="Usuario"),
    path('registro-empleado/', views.registro_empleado, name='registro_empleado'),
]

