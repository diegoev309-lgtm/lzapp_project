from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_producciones, name="listar_producciones"),
    path('nuevo/', views.crear_produccion, name="crear_produccion"),
    #path('exportar-pdf/', views.exportar_produccion_pdf, name="exportar_produccion_pdf"),
    path('importar/', views.importar_produccion, name='importar_produccion'),
    path('importadas/', views.producciones_importadas, name='producciones_importadas'),
    path('graficos/',views.graficos_produccion,name='graficos_produccion'),
    path('graficos/productos-disponibles/', views.productos_produccion_disponibles, name='productos_produccion_disponibles'),
    path('graficos/producto/', views.grafico_produccion_producto, name='grafico_produccion_producto'),
    path('graficos/proyeccion/', views.grafico_proyeccion_produccion, name='grafico_proyeccion_produccion'),
]