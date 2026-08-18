from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_producciones, name="listar_producciones"),
    path('nuevo/', views.crear_produccion, name="crear_produccion"),
    #path('exportar-pdf/', views.exportar_produccion_pdf, name="exportar_produccion_pdf"),
    path('importar/', views.importar_produccion, name='importar_produccion'),
    path('importadas/', views.producciones_importadas, name='producciones_importadas'),
    path('graficos/',views.graficos_produccion,name='graficos_produccion'),
]