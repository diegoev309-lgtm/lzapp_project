from django.urls import path,include
from . import views

urlpatterns = [
    path('dview',views.dview,name="dview"),
    path('Inicio',views.Inicio,name="Inicio_dash"),
    path('Pedidos',views.Pedidos,name="Pedidos"),
    path('Notificaciones',views.Notificaciones,name="Notificaciones"),

    # ---- API JSON para los gráficos Plotly de Inicio ----
    path('api/ventas-mensuales', views.api_ventas_mensuales, name="api_ventas_mensuales"),
    path('api/ventas-dia/<int:anio>/<int:mes>', views.api_ventas_dia, name="api_ventas_dia"),
    path('api/distribucion-productos', views.api_distribucion_productos, name="api_distribucion_productos"),
    path('api/stock-flujo', views.api_stock_flujo, name="api_stock_flujo"),
    path('api/pedidos-tiempo-real', views.api_pedidos_tiempo_real, name="api_pedidos_tiempo_real"),
]