"""Reportes del negocio, en un solo lugar.

Antes cada módulo tenía su propio botón de PDF: cuatro no hacían nada
(apuntaban a "#") y el de Descuentos sí funcionaba pero tampoco era
alcanzable, porque su botón también apuntaba a "#". Toda esa capacidad
vive ahora acá, con un formato común.

Cada reporte declara sus columnas y devuelve filas ya formateadas, así el
PDF no tiene que saber de dónde salió cada dato.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models import Count, F, Sum
from django.utils import timezone

from dashboard.models import (
    CampanaDescuento, DetalleVenta, Pedido, Producto, Produccion, Venta,
)


def rango_desde_peticion(request):
    """Período del reporte: ?desde= y ?hasta= (por defecto, últimos 30 días)."""
    hoy = timezone.localdate()

    def leer(clave, defecto):
        valor = request.GET.get(clave)
        if not valor:
            return defecto
        try:
            return date.fromisoformat(valor)
        except ValueError:
            return defecto

    desde = leer('desde', hoy - timedelta(days=29))
    hasta = leer('hasta', hoy)

    # Si vienen al revés se intercambian, en vez de devolver un reporte
    # vacío que parecería "no hay datos".
    if desde > hasta:
        desde, hasta = hasta, desde
    return desde, hasta


def _dinero(valor):
    return f'$ {Decimal(valor or 0):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


# ---------------------------------------------------------------
# Constructores: cada uno devuelve el mismo contrato
#   {titulo, descripcion, resumen: [(etiqueta, valor)], columnas: [...],
#    filas: [[...]], }
# ---------------------------------------------------------------
def reporte_ventas(desde, hasta):
    ventas = (Venta.objects
              .filter(fecha__date__gte=desde, fecha__date__lte=hasta)
              .exclude(pedido__estado=Pedido.Estado.CANCELADO)
              .select_related('usuario')
              .prefetch_related('detalles__producto')
              .order_by('-fecha'))

    total = ventas.aggregate(t=Sum('total'))['t'] or Decimal(0)
    unidades = (DetalleVenta.objects
                .filter(venta__in=ventas)
                .aggregate(t=Sum('cantidad'))['t'] or 0)

    filas = []
    for v in ventas:
        articulos = sum(d.cantidad for d in v.detalles.all())
        filas.append([
            f'#{v.id}',
            timezone.localtime(v.fecha).strftime('%d/%m/%Y %H:%M'),
            v.usuario.get_full_name() or v.usuario.username,
            str(articulos),
            _dinero(v.total),
        ])

    return {
        'titulo': 'Reporte de ventas',
        'descripcion': 'Ventas registradas en el período, sin contar las canceladas.',
        'resumen': [
            ('Ventas', ventas.count()),
            ('Unidades vendidas', unidades),
            ('Ingresos', _dinero(total)),
            ('Ticket promedio', _dinero(total / ventas.count()) if ventas.count() else _dinero(0)),
        ],
        'columnas': ['Venta', 'Fecha', 'Cliente', 'Artículos', 'Total'],
        'filas': filas,
    }


def reporte_productos(desde, hasta):
    productos = Producto.objects.all().order_by('nombre')
    bajo_stock = productos.filter(stock_actual__lt=F('stock_minimo'))

    filas = [[
        p.nombre,
        _dinero(p.precio),
        str(p.stock_actual or 0),
        str(p.stock_minimo or 0),
        'Sí' if p.disponibilidad else 'No',
        'Bajo mínimo' if (p.stock_actual or 0) < (p.stock_minimo or 0) else 'Normal',
    ] for p in productos]

    return {
        'titulo': 'Reporte de inventario',
        'descripcion': 'Estado actual del catálogo. No depende del período elegido.',
        'resumen': [
            ('Productos', productos.count()),
            ('Bajo el mínimo', bajo_stock.count()),
            ('Agotados', productos.filter(stock_actual=0).count()),
            ('Unidades en stock', productos.aggregate(t=Sum('stock_actual'))['t'] or 0),
        ],
        'columnas': ['Producto', 'Precio', 'Stock', 'Mínimo', 'Disponible', 'Estado'],
        'filas': filas,
    }


def reporte_produccion(desde, hasta):
    lotes = (Produccion.objects
             .filter(fecha_produccion__date__gte=desde, fecha_produccion__date__lte=hasta)
             .select_related('producto')
             .order_by('-fecha_produccion'))

    filas = [[
        f'#{l.id}',
        l.producto.nombre,
        str(l.cantidad_producida),
        timezone.localtime(l.fecha_produccion).strftime('%d/%m/%Y'),
        l.fecha_vencimiento.strftime('%d/%m/%Y') if l.fecha_vencimiento else '—',
        (l.observacion or '—')[:60],
    ] for l in lotes]

    return {
        'titulo': 'Reporte de producción',
        'descripcion': 'Lotes producidos en el período.',
        'resumen': [
            ('Lotes', lotes.count()),
            ('Unidades producidas', lotes.aggregate(t=Sum('cantidad_producida'))['t'] or 0),
            ('Productos distintos', lotes.values('producto').distinct().count()),
        ],
        'columnas': ['Lote', 'Producto', 'Cantidad', 'Producido', 'Vence', 'Observación'],
        'filas': filas,
    }


def reporte_pedidos(desde, hasta):
    pedidos = (Pedido.objects
               .filter(fecha_creacion__date__gte=desde, fecha_creacion__date__lte=hasta)
               .select_related('venta', 'venta__usuario', 'repartidor')
               .order_by('-fecha_creacion'))

    filas = [[
        f'#{p.id}',
        timezone.localtime(p.fecha_creacion).strftime('%d/%m/%Y %H:%M'),
        p.venta.usuario.get_full_name() or p.venta.usuario.username,
        p.get_estado_display(),
        (p.repartidor.get_full_name() or p.repartidor.username) if p.repartidor else 'Sin asignar',
        _dinero(p.venta.total),
    ] for p in pedidos]

    por_estado = {e['estado']: e['n'] for e in
                  pedidos.values('estado').annotate(n=Count('id'))}

    return {
        'titulo': 'Reporte de pedidos',
        'descripcion': 'Pedidos creados en el período y en qué terminaron.',
        'resumen': [
            ('Pedidos', pedidos.count()),
            ('Entregados', por_estado.get(Pedido.Estado.ENTREGADO, 0)),
            ('En camino', por_estado.get(Pedido.Estado.EN_CAMINO, 0)),
            ('Cancelados', por_estado.get(Pedido.Estado.CANCELADO, 0)),
        ],
        'columnas': ['Pedido', 'Fecha', 'Cliente', 'Estado', 'Repartidor', 'Total'],
        'filas': filas,
    }


def reporte_campanas(desde, hasta):
    campanas = (CampanaDescuento.objects
                .all()
                .prefetch_related('productos')
                .order_by('-activo', 'nombre'))

    filas = [[
        c.nombre,
        f'{c.porcentaje_descuento}%',
        ', '.join(p.nombre for p in c.productos.all()[:4]) or '—',
        c.get_frecuencia_display(),
        'Activa' if c.activo else 'Inactiva',
        c.fecha_inicio.strftime('%d/%m/%Y'),
    ] for c in campanas]

    return {
        'titulo': 'Reporte de campañas de descuento',
        'descripcion': 'Todas las campañas registradas. No depende del período elegido.',
        'resumen': [
            ('Campañas', campanas.count()),
            ('Activas', campanas.filter(activo=True).count()),
            ('Inactivas', campanas.filter(activo=False).count()),
        ],
        'columnas': ['Campaña', 'Descuento', 'Productos', 'Frecuencia', 'Estado', 'Desde'],
        'filas': filas,
    }


def reporte_usuarios(desde, hasta):
    usuarios = (User.objects
                .filter(date_joined__date__gte=desde, date_joined__date__lte=hasta)
                .order_by('-date_joined'))

    filas = [[
        u.username,
        u.email or '—',
        'Empleado' if hasattr(u, 'perfilemple') and u.perfilemple.rol == 'empleado'
        else ('Administrador' if u.is_staff else 'Cliente'),
        'Sí' if u.is_active else 'No',
        timezone.localtime(u.date_joined).strftime('%d/%m/%Y'),
    ] for u in usuarios]

    return {
        'titulo': 'Reporte de usuarios registrados',
        'descripcion': 'Cuentas creadas en el período.',
        'resumen': [
            ('Registrados', usuarios.count()),
            ('Activos', usuarios.filter(is_active=True).count()),
            ('Total en el sistema', User.objects.count()),
        ],
        'columnas': ['Usuario', 'Correo', 'Rol', 'Activo', 'Registro'],
        'filas': filas,
    }


# El catálogo que ve el módulo: clave, etiqueta, icono, y si usa el período.
REPORTES = {
    'ventas':     ('Ventas',      'bi-cash-stack',     True,  reporte_ventas),
    'pedidos':    ('Pedidos',     'bi-truck',          True,  reporte_pedidos),
    'produccion': ('Producción',  'bi-box-seam-fill',  True,  reporte_produccion),
    'productos':  ('Inventario',  'bi-basket-fill',    False, reporte_productos),
    'campanas':   ('Campañas',    'bi-tags-fill',      False, reporte_campanas),
    'usuarios':   ('Usuarios',    'bi-people-fill',    True,  reporte_usuarios),
}


def construir(clave, desde, hasta):
    """Arma el reporte pedido, o None si la clave no existe."""
    entrada = REPORTES.get(clave)
    if not entrada:
        return None

    _, _, usa_periodo, constructor = entrada
    datos = constructor(desde, hasta)
    datos['usa_periodo'] = usa_periodo
    datos['desde'] = desde
    datos['hasta'] = hasta
    datos['generado'] = timezone.now()
    return datos
