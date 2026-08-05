from django.urls import path
from . import views

urlpatterns = [
    path('', views.panel_descuentos, name='panel_descuentos'),
    path('campana/nueva/', views.crear_campana_descuento, name='crear_campana_descuento'),
    path('campana/<int:pk>/editar/', views.editar_campana_descuento, name='editar_campana_descuento'),
    path('campana/<int:pk>/eliminar/', views.eliminar_campana_descuento, name='eliminar_campana_descuento'),
    path('campana/<int:pk>/toggle/', views.toggle_campana_descuento, name='toggle_campana_descuento'),
    path('producto/<int:pk>/previsualizar/', views.previsualizar_producto, name='previsualizar_producto'),
    path('premio/marcar-mostrado/', views.marcar_premio_mostrado, name='marcar_premio_mostrado'),
]