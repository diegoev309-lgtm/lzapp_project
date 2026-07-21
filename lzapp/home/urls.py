from django.urls import path
from home.views import main, user, client, carro, buscar_productos_ajax, home

urlpatterns = [
    path('main', main, name="main"),
    path('user', user, name="user"),
    path('client', client, name="client"),
    path('carro', carro, name="carro"),
    path('buscar-ajax/', buscar_productos_ajax, name="buscar_ajax"),
    path('', home, name="home"),
]