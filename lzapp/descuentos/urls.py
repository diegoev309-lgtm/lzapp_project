from django.urls import path
from . import views

urlpatterns = [
    path('descuentos/', views.listar_descuentos, name='listar_descuentos'),
    path('descuentos/<int:producto_id>/aplicar/', views.aplicar_descuento, name='aplicar_descuento'),
    path('descuentos/<int:descuento_id>/quitar/', views.quitar_descuento, name='quitar_descuento'),
    path('descuentos/reglas/<int:regla_id>/toggle/', views.toggle_regla_descuento, name='toggle_regla_descuento'),
    path('descuentos/reglas/nueva/', views.crear_regla_descuento, name='crear_regla_descuento'),
    path('descuentos/reglas/<int:regla_id>/editar/', views.editar_regla_descuento, name='editar_regla_descuento'),
    path('descuentos/reglas/<int:regla_id>/eliminar/', views.eliminar_regla_descuento, name='eliminar_regla_descuento'),
]