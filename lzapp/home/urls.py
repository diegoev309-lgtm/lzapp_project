from django.urls import path
from home.views import main, user, client, carro, buscar_productos_ajax #home

urlpatterns = [
    path('', user, name="user"),
    path('main', main, name="main"),
    path('client', client, name="client"),
    path('carro', carro, name="carro"),
    path('buscar-ajax/', buscar_productos_ajax, name="buscar_ajax"),
]