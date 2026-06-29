from django.urls import path
from . import views

urlpatterns=[
    path('',views.listar_productos,name="listar_productos"),
    path('nuevo/',views.crear_producto,name="crear_producto"),
    path('editar/<int:id>/',views.editar_producto,name="editar_producto"),
    path('eliminar/<int:id>/',views.eliminar_producto,name="eliminar_producto"),
]