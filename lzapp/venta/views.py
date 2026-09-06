import json
from datetime import date, timedelta
from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from dashboard.models import DetalleVenta, Venta
from dashboard.paginacion import leer_por_pagina
from seguridad.decorators import vista_dashboard

TOP_PRODUCTOS_CANTIDAD = 5


def _rango_fechas(request):
    """
    Calcula el rango de fechas [desde, hasta] según el filtro elegido:
    'semana' (últimos 7 días), 'mes' (últimos 30 días, por defecto) o
    'rango' (fechas personalizadas por GET: desde=YYYY-MM-DD&hasta=YYYY-MM-DD).
    """
    filtro = request.GET.get('filtro', 'mes')
    hoy = timezone.now().date()

    if filtro == 'semana':
        desde = hoy - timedelta(days=6)
        hasta = hoy
    elif filtro == 'rango':
        desde_str = request.GET.get('desde')
        hasta_str = request.GET.get('hasta')
        try:
            desde = date.fromisoformat(desde_str) if desde_str else hoy - timedelta(days=29)
        except ValueError:
            desde = hoy - timedelta(days=29)
        try:
            hasta = date.fromisoformat(hasta_str) if hasta_str else hoy
        except ValueError:
            hasta = hoy
    else:
        filtro = 'mes'
        desde = hoy - timedelta(days=29)
        hasta = hoy

    return filtro, desde, hasta


def _top_productos(detalles_qs, cantidad=TOP_PRODUCTOS_CANTIDAD):
    return list(
        detalles_qs
        .values('producto__id', 'producto__nombre')
        .annotate(unidades=Sum('cantidad'), ingresos=Sum('subtotal'))
        .order_by('-ingresos')[:cantidad]
    )


def _resumen_diario(detalles_qs, ventas_qs):
    """
    Arma un resumen por día (ventas, ingresos, unidades, ticket promedio)
    SIN exponer qué cliente compró qué. Reemplaza al viejo listado de
    ventas por cliente: es la info que de verdad sirve para ver el
    comportamiento del negocio día a día.
    """
    combinado = {}

    ingresos_por_dia = (
        detalles_qs
        .annotate(dia=TruncDate('venta__fecha'))
        .values('dia')
        .annotate(total=Sum('subtotal'))
    )
    for item in ingresos_por_dia:
        combinado.setdefault(item['dia'], {'ingresos': Decimal('0'), 'ventas': 0, 'unidades': 0})
        combinado[item['dia']]['ingresos'] = item['total'] or Decimal('0')

    unidades_por_dia = (
        detalles_qs
        .annotate(dia=TruncDate('venta__fecha'))
        .values('dia')
        .annotate(total=Sum('cantidad'))
    )
    for item in unidades_por_dia:
        combinado.setdefault(item['dia'], {'ingresos': Decimal('0'), 'ventas': 0, 'unidades': 0})
        combinado[item['dia']]['unidades'] = item['total'] or 0

    # El conteo de ventas por día se hace en Python (no encadenado a las
    # otras dos agregaciones) para evitar resultados cruzados al mezclar
    # varios .annotate(Sum) sobre distintos values() en la misma consulta.
    for v in ventas_qs.annotate(dia=TruncDate('fecha')).values('dia'):
        dia = v['dia']
        combinado.setdefault(dia, {'ingresos': Decimal('0'), 'ventas': 0, 'unidades': 0})
        combinado[dia]['ventas'] += 1

    resumen = []
    for dia in sorted(combinado.keys(), reverse=True):
        info = combinado[dia]
        ticket_promedio = (info['ingresos'] / info['ventas']) if info['ventas'] else Decimal('0')
        resumen.append({
            'fecha': dia,
            'ventas': info['ventas'],
            'ingresos': info['ingresos'],
            'unidades': info['unidades'],
            'ticket_promedio': ticket_promedio,
        })
    return resumen


def construir_contexto_ganancias(request):
    """
    Calcula todo lo relacionado a "ganancias" (ingresos totales, ya que
    no hay campo de costo registrado en Producto): KPIs, series diarias
    para los gráficos, el resumen diario y el top de productos más
    vendidos, según el período elegido. Se separa en su propia función
    porque tanto el panel en pantalla como el PDF (solo de ganancias)
    usan estos mismos datos.
    """
    filtro, desde, hasta = _rango_fechas(request)

    detalles_qs = DetalleVenta.objects.filter(
        venta__fecha__date__gte=desde,
        venta__fecha__date__lte=hasta,
    )
    ventas_qs = Venta.objects.filter(
        fecha__date__gte=desde,
        fecha__date__lte=hasta,
    )

    # ---------- KPIs ----------
    total_ingresos = detalles_qs.aggregate(total=Sum('subtotal'))['total'] or Decimal('0')
    cantidad_ventas = ventas_qs.count()
    unidades_vendidas = detalles_qs.aggregate(total=Sum('cantidad'))['total'] or 0
    ticket_promedio = (total_ingresos / cantidad_ventas) if cantidad_ventas else Decimal('0')

    # ---------- Ingresos por día (gráfico de línea) ----------
    ingresos_por_dia = (
        detalles_qs
        .annotate(dia=TruncDate('venta__fecha'))
        .values('dia')
        .annotate(total=Sum('subtotal'))
        .order_by('dia')
    )
    etiquetas_ingresos = [item['dia'].strftime('%d/%m') for item in ingresos_por_dia]
    valores_ingresos = [float(item['total']) for item in ingresos_por_dia]
    fechas_ingresos = [item['dia'].isoformat() for item in ingresos_por_dia]

    # ---------- Ventas por día (gráfico de barras) ----------
    conteo_por_dia = {}
    for v in ventas_qs.annotate(dia=TruncDate('fecha')).values('dia'):
        conteo_por_dia[v['dia']] = conteo_por_dia.get(v['dia'], 0) + 1
    dias_ordenados = sorted(conteo_por_dia.keys())
    etiquetas_ventas = [d.strftime('%d/%m') for d in dias_ordenados]
    valores_ventas = [conteo_por_dia[d] for d in dias_ordenados]
    fechas_ventas = [d.isoformat() for d in dias_ordenados]

    # ---------- Top productos ----------
    top_productos = _top_productos(detalles_qs)

    # ---------- Dona: participación de los top 5 en los ingresos ----------
    suma_top = sum(item['ingresos'] for item in top_productos) if top_productos else Decimal('0')
    otros = total_ingresos - suma_top
    etiquetas_dona = [item['producto__nombre'] for item in top_productos]
    valores_dona = [float(item['ingresos']) for item in top_productos]
    if otros > 0:
        etiquetas_dona.append('Otros productos')
        valores_dona.append(float(otros))

    # ---------- Resumen diario (reemplaza el viejo listado por cliente) ----------
    resumen_diario = _resumen_diario(detalles_qs, ventas_qs)

    return {
        'filtro': filtro,
        'desde': desde,
        'hasta': hasta,
        'total_ingresos': total_ingresos,
        'cantidad_ventas': cantidad_ventas,
        'unidades_vendidas': unidades_vendidas,
        'ticket_promedio': ticket_promedio,
        'top_productos': top_productos,
        'resumen_diario': resumen_diario,
        'etiquetas_ingresos_json': json.dumps(etiquetas_ingresos),
        'valores_ingresos_json': json.dumps(valores_ingresos),
        'fechas_ingresos_json': json.dumps(fechas_ingresos),
        'etiquetas_ventas_json': json.dumps(etiquetas_ventas),
        'valores_ventas_json': json.dumps(valores_ventas),
        'fechas_ventas_json': json.dumps(fechas_ventas),
        'etiquetas_dona_json': json.dumps(etiquetas_dona),
        'valores_dona_json': json.dumps(valores_dona),
    }


@vista_dashboard
def panel_ventas(request):
    contexto = construir_contexto_ganancias(request)

    # Lo elige el usuario desde el pie de la tabla (10 por defecto). Antes
    # eran 3 días fijos por página, que con un mes de ventas obligaba a
    # pasar diez páginas para ver el período completo.
    paginator = Paginator(contexto['resumen_diario'], leer_por_pagina(request))
    contexto['resumen_diario_pagina'] = paginator.get_page(request.GET.get('page'))

    return render(request, 'panel_ventas.html', contexto)


@vista_dashboard
def detalle_dia_ventas(request):
    """
    Endpoint JSON: al hacer clic en un punto del gráfico o en una fila
    del historial diario, devuelve el detalle de UN día específico —
    ingresos, cantidad de ventas y top productos de esa fecha — sin
    tener que navegar a otra página.
    """
    fecha_str = request.GET.get('fecha', '').strip()
    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'fecha inválida'}, status=400)

    detalles_qs = DetalleVenta.objects.filter(venta__fecha__date=fecha)
    ventas_qs = Venta.objects.filter(fecha__date=fecha)

    total_ingresos = detalles_qs.aggregate(total=Sum('subtotal'))['total'] or Decimal('0')
    cantidad_ventas = ventas_qs.count()
    unidades_vendidas = detalles_qs.aggregate(total=Sum('cantidad'))['total'] or 0
    top_productos = _top_productos(detalles_qs, cantidad=5)

    return JsonResponse({
        'ok': True,
        'fecha': fecha.strftime('%d/%m/%Y'),
        'total_ingresos': float(total_ingresos),
        'cantidad_ventas': cantidad_ventas,
        'unidades_vendidas': unidades_vendidas,
        'top_productos': [
            {
                'nombre': item['producto__nombre'],
                'unidades': item['unidades'],
                'ingresos': float(item['ingresos']),
            }
            for item in top_productos
        ],
    })