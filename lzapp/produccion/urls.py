from django.urls import path
from . import views

urlpatterns=[
    path('',views.listar_producciones,name="listar_producciones"),
    path('nuevo/',views.crear_produccion,name="crear_produccion"),
]