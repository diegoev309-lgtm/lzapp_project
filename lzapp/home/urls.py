from django.urls import path
from . import views


urlpatterns = [
    path('',views.user, name="user"),
    path('main',views.main, name="main"),
    path('client',views.client, name="client"),
    path('carro',views.carro, name="carro"),
    path('buscar-ajax/',views.buscar_productos_ajax, name="buscar_ajax"),
]