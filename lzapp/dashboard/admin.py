from django.contrib import admin

from .models import (
    Perfil, PerfilEmple, Producto, Produccion,
    Venta, DetalleVenta, Pedido, CampanaDescuento, DescuentoAsignado,
    Calificacion, TiradaDiaria, PremioRuletaDiaria,
)


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = ('subtotal',)


class PedidoInline(admin.StackedInline):
    model = Pedido
    extra = 0
    can_delete = False
    fields = ('estado', 'repartidor', 'direccion_entrega', 'incidencia')


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'fecha', 'total', 'estado_pedido', 'repartidor_pedido')
    search_fields = ('usuario__username', 'id')
    inlines = [DetalleVentaInline, PedidoInline]

    @admin.display(description='Estado del pedido')
    def estado_pedido(self, obj):
        return obj.pedido.get_estado_display() if hasattr(obj, 'pedido') else '—'

    @admin.display(description='Repartidor')
    def repartidor_pedido(self, obj):
        if hasattr(obj, 'pedido') and obj.pedido.repartidor:
            return obj.pedido.repartidor.get_full_name() or obj.pedido.repartidor.username
        return 'Sin asignar'


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'venta', 'estado', 'repartidor', 'incidencia', 'fecha_actualizacion')
    list_filter = ('estado', 'repartidor')
    list_editable = ('estado', 'repartidor', 'incidencia')
    search_fields = ('venta__id', 'venta__usuario__username')


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'stock_actual', 'stock_minimo', 'disponibilidad')
    list_filter = ('disponibilidad',)
    search_fields = ('nombre',)


@admin.register(Produccion)
class ProduccionAdmin(admin.ModelAdmin):
    list_display = ('producto', 'cantidad_producida', 'fecha_produccion')
    list_filter = ('producto',)


@admin.register(CampanaDescuento)
class CampanaDescuentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'frecuencia', 'activo', 'fecha_inicio', 'fecha_fin')
    list_filter = ('activo', 'frecuencia')
    filter_horizontal = ('productos',)


@admin.register(PremioRuletaDiaria)
class PremioRuletaDiariaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'peso', 'activo', 'fecha_actualizacion')
    list_filter = ('activo',)
    list_editable = ('peso', 'activo')


admin.site.register(Perfil)
admin.site.register(PerfilEmple)
admin.site.register(DescuentoAsignado)
admin.site.register(Calificacion)
admin.site.register(TiradaDiaria)
