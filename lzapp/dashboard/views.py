import calendar
from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone

from .models import Venta, DetalleVenta, Producto, Produccion, Pedido, CampanaDescuento
from seguridad.decorators import vista_dashboard

MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
            'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


@vista_dashboard
def dview(request):
    return redirect('Inicio_dash')


# =========================================================
# VISTAS DE PÁGINA
# =========================================================

@vista_dashboard
def Inicio(request):
    hoy = timezone.now()

    # ---- Ventas del mes vs. mes anterior (tarjeta 1) ----
    ventas_mes = (Venta.objects
                  .filter(fecha__year=hoy.year, fecha__month=hoy.month)
                  .exclude(pedido__estado=Pedido.Estado.CANCELADO)
                  .aggregate(total=Sum('total'))['total']) or 0

    mes_ant = hoy.month - 1 or 12
    anio_ant = hoy.year if hoy.month > 1 else hoy.year - 1
    ventas_mes_ant = (Venta.objects
                       .filter(fecha__year=anio_ant, fecha__month=mes_ant)
                       .exclude(pedido__estado=Pedido.Estado.CANCELADO)
                       .aggregate(total=Sum('total'))['total']) or 0

    if ventas_mes_ant > 0:
        variacion_ventas = round(((float(ventas_mes) - float(ventas_mes_ant)) / float(ventas_mes_ant)) * 100, 1)
    else:
        variacion_ventas = 100.0 if ventas_mes > 0 else 0.0

    # ---- Pedidos recibidos en la semana (tarjeta 2) ----
    hace_7_dias = hoy - timedelta(days=7)
    hace_14_dias = hoy - timedelta(days=14)
    pedidos_semana = Venta.objects.filter(fecha__gte=hace_7_dias).count()
    pedidos_semana_previa = Venta.objects.filter(fecha__gte=hace_14_dias, fecha__lt=hace_7_dias).count()
    diferencia_pedidos = pedidos_semana - pedidos_semana_previa

    # ---- Campañas activas / inactivas (tarjeta 3) ----
    campanas_totales = CampanaDescuento.objects.count()
    campanas_activas = sum(1 for c in CampanaDescuento.objects.all() if c.esta_vigente())
    campanas_inactivas = campanas_totales - campanas_activas

    # ---- Usuarios que entraron esta semana (tarjeta 4) ----
    usuarios_totales = User.objects.count()
    usuarios_activos_semana = User.objects.filter(last_login__gte=hace_7_dias).count()

    contexto = {
        'ventas_mes': ventas_mes,
        'variacion_ventas': variacion_ventas,
        'pedidos_semana': pedidos_semana,
        'diferencia_pedidos': diferencia_pedidos,
        'campanas_totales': campanas_totales,
        'campanas_activas': campanas_activas,
        'campanas_inactivas': campanas_inactivas,
        'usuarios_totales': usuarios_totales,
        'usuarios_activos_semana': usuarios_activos_semana,
    }
    return render(request, "inicio.html", contexto)

# =========================================================
# API (JSON) — alimentan los gráficos Plotly de Inicio
# =========================================================

@vista_dashboard
def api_ventas_mensuales(request):
    """Ventas reales agrupadas por mes para el año pedido (para el gráfico Plotly principal)."""
    hoy = timezone.now()
    anio = int(request.GET.get('anio', hoy.year))

    ventas_qs = (Venta.objects
                 .filter(fecha__year=anio)
                 .exclude(pedido__estado=Pedido.Estado.CANCELADO)
                 .values('fecha__month')
                 .annotate(total=Sum('total'), pedidos=Count('id')))
    ventas_por_mes = {row['fecha__month']: row for row in ventas_qs}

    problemas_qs = (Pedido.objects
                     .filter(venta__fecha__year=anio)
                     .exclude(Q(incidencia__isnull=True) | Q(incidencia=''))
                     .values('venta__fecha__month')
                     .annotate(n=Count('id')))
    problemas_por_mes = {row['venta__fecha__month']: row['n'] for row in problemas_qs}

    data = {
        'anio': anio,
        'meses': MESES_ES,
        'ventas': [float(ventas_por_mes.get(m, {}).get('total') or 0) for m in range(1, 13)],
        'pedidos': [int(ventas_por_mes.get(m, {}).get('pedidos') or 0) for m in range(1, 13)],
        'problemas': [int(problemas_por_mes.get(m, 0)) for m in range(1, 13)],
    }
    return JsonResponse(data)


@vista_dashboard
def api_ventas_dia(request, anio, mes):
    """Detalle día a día de un mes: ventas, N° de pedidos y problemas/incidencias reportadas."""
    dias_en_mes = calendar.monthrange(int(anio), int(mes))[1]

    ventas_qs = (Venta.objects
                 .filter(fecha__year=anio, fecha__month=mes)
                 .exclude(pedido__estado=Pedido.Estado.CANCELADO)
                 .values('fecha__day')
                 .annotate(total=Sum('total'), pedidos=Count('id')))
    ventas_por_dia = {row['fecha__day']: row for row in ventas_qs}

    incidencias_qs = (Pedido.objects
                       .filter(venta__fecha__year=anio, venta__fecha__month=mes)
                       .exclude(Q(incidencia__isnull=True) | Q(incidencia=''))
                       .values('venta__fecha__day', 'venta_id', 'incidencia', 'estado'))
    problemas_por_dia = {}
    for row in incidencias_qs:
        problemas_por_dia.setdefault(row['venta__fecha__day'], []).append({
            'pedido_id': row['venta_id'],
            'texto': row['incidencia'],
            'estado': row['estado'],
        })

    dias = list(range(1, dias_en_mes + 1))
    data = {
        'anio': int(anio),
        'mes': int(mes),
        'nombre_mes': MESES_ES[int(mes) - 1],
        'dias': dias,
        'ventas': [float(ventas_por_dia.get(d, {}).get('total') or 0) for d in dias],
        'pedidos': [int(ventas_por_dia.get(d, {}).get('pedidos') or 0) for d in dias],
        'problemas': [len(problemas_por_dia.get(d, [])) for d in dias],
        'detalle_problemas': problemas_por_dia,
    }
    return JsonResponse(data)


@vista_dashboard
def api_distribucion_productos(request):
    """Participación (%) de cada producto del catálogo, según ingresos reales por ventas."""
    ingresos = (DetalleVenta.objects
                .values('producto_id')
                .annotate(ingreso=Sum('subtotal'), unidades=Sum('cantidad')))
    ingreso_por_producto = {r['producto_id']: r for r in ingresos}

    productos = list(Producto.objects.all())
    total_ingreso = sum(float(ingreso_por_producto.get(p.id, {}).get('ingreso') or 0) for p in productos)

    etiquetas, valores, unidades, modo = [], [], [], 'ingresos'

    if total_ingreso > 0:
        for p in productos:
            info = ingreso_por_producto.get(p.id, {})
            etiquetas.append(p.nombre)
            valores.append(float(info.get('ingreso') or 0))
            unidades.append(int(info.get('unidades') or 0))
    else:
        # Sin historial de ventas todavía: se usa el stock actual como referencia de participación
        modo = 'stock'
        for p in productos:
            etiquetas.append(p.nombre)
            valores.append(int(p.stock_actual or 0))
            unidades.append(int(p.stock_actual or 0))

    return JsonResponse({'etiquetas': etiquetas, 'valores': valores, 'unidades': unidades, 'modo': modo})


@vista_dashboard
def api_stock_flujo(request):
    """Entradas (producción) vs. salidas (ventas) de stock, día a día, de los últimos 14 días."""
    dias_atras = int(request.GET.get('dias', 14))
    hoy = timezone.localdate()
    fechas = [hoy - timedelta(days=i) for i in range(dias_atras - 1, -1, -1)]

    entradas_qs = (Produccion.objects
                   .filter(fecha_produccion__date__gte=fechas[0])
                   .values('fecha_produccion__date')
                   .annotate(total=Sum('cantidad_producida')))
    entradas_por_dia = {r['fecha_produccion__date']: r['total'] for r in entradas_qs}

    salidas_qs = (DetalleVenta.objects
                  .filter(venta__fecha__date__gte=fechas[0])
                  .exclude(venta__pedido__estado=Pedido.Estado.CANCELADO)
                  .values('venta__fecha__date')
                  .annotate(total=Sum('cantidad')))
    salidas_por_dia = {r['venta__fecha__date']: r['total'] for r in salidas_qs}

    stock_total = Producto.objects.aggregate(t=Sum('stock_actual'))['t'] or 0
    entradas_totales = Produccion.objects.filter(fecha_produccion__date__gte=fechas[0]).aggregate(
        t=Sum('cantidad_producida'))['t'] or 0
    salidas_totales = DetalleVenta.objects.filter(venta__fecha__date__gte=fechas[0]).exclude(
        venta__pedido__estado=Pedido.Estado.CANCELADO).aggregate(t=Sum('cantidad'))['t'] or 0

    data = {
        'dias': [f.strftime('%d/%m') for f in fechas],
        'entradas': [int(entradas_por_dia.get(f, 0) or 0) for f in fechas],
        'salidas': [int(salidas_por_dia.get(f, 0) or 0) for f in fechas],
        'stock_total': int(stock_total),
        'entradas_totales': int(entradas_totales),
        'salidas_totales': int(salidas_totales),
    }
    return JsonResponse(data)


@vista_dashboard
def api_pedidos_tiempo_real(request):
    """Estado en vivo de los últimos pedidos: repartidor asignado y avance de la entrega."""
    pedidos = (Pedido.objects
               .select_related('venta', 'venta__usuario', 'repartidor')
               .prefetch_related('venta__detalles')
               .order_by('-fecha_creacion')[:20])

    lista = []
    for ped in pedidos:
        venta = ped.venta
        n_items = sum(d.cantidad for d in venta.detalles.all())
        lista.append({
            'id': venta.id,
            'pedido_id': ped.id,
            'cliente': venta.usuario.get_full_name() or venta.usuario.username,
            'fecha': timezone.localtime(venta.fecha).strftime('%d/%m %H:%M'),
            'total': float(venta.total),
            'estado': ped.estado,
            'estado_display': ped.get_estado_display(),
            'repartidor': (ped.repartidor.get_full_name() or ped.repartidor.username) if ped.repartidor else None,
            'items': n_items,
            'incidencia': ped.incidencia,
        })

    resumen = {
        'pendientes': sum(1 for p in lista if p['estado'] in ('pendiente', 'preparando')),
        'en_camino': sum(1 for p in lista if p['estado'] == 'en_camino'),
        'entregados': sum(1 for p in lista if p['estado'] == 'entregado'),
        'cancelados': sum(1 for p in lista if p['estado'] == 'cancelado'),
    }

    return JsonResponse({'pedidos': lista, 'resumen': resumen})
