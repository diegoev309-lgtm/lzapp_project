import json

from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate, TruncWeek
from django.contrib import messages
from openpyxl import load_workbook

from dashboard.models import Produccion, Producto, DetalleVenta
from produccion.forms import ProduccionForm
from .forms import ImportarProduccionForm

UMBRAL_DIAS_STOCK = 7       # por debajo de esto, alertamos "reforzar producción"
VENTANA_RITMO_VENTAS = 30   # días hacia atrás para medir el ritmo de venta real
DIAS_SIN_PRODUCCION = 7     # productos sin producción en esta cantidad de días


def _resolver_periodo(request):
    """Traduce el filtro de la barra de controles (semana/mes/rango) en un
    rango de fechas concreto. Se reutiliza en la vista y en el PDF."""
    filtro = request.GET.get('filtro', 'mes')
    hoy = timezone.now().date()

    if filtro == 'semana':
        desde = hoy - timedelta(days=6)
        hasta = hoy
    elif filtro == 'rango':
        try:
            desde = datetime.strptime(request.GET.get('desde'), '%Y-%m-%d').date()
            hasta = datetime.strptime(request.GET.get('hasta'), '%Y-%m-%d').date()
        except (TypeError, ValueError):
            filtro = 'mes'
            desde = hoy - timedelta(days=29)
            hasta = hoy
    else:
        filtro = 'mes'
        desde = hoy - timedelta(days=29)
        hasta = hoy

    return filtro, desde, hasta


def _calcular_alertas():
    """Compara el stock actual contra el ritmo real de ventas (últimos 30
    días) para avisar qué productos hay que reforzar, y revisa cuáles no
    tuvieron producción registrada en la última semana."""
    hoy = timezone.now().date()
    desde_ventas = hoy - timedelta(days=VENTANA_RITMO_VENTAS - 1)

    ventas_por_producto = {
        fila['producto_id']: fila['unidades']
        for fila in (
            DetalleVenta.objects
            .filter(venta__fecha__date__gte=desde_ventas)
            .values('producto_id')
            .annotate(unidades=Sum('cantidad'))
        )
    }

    productos_activos = Producto.objects.filter(disponibilidad=True)

    # -- productos a los que hay que subirle la producción --
    productos_criticos = []
    for producto in productos_activos:
        unidades_vendidas = ventas_por_producto.get(producto.id, 0)
        if unidades_vendidas <= 0:
            continue  # sin ventas recientes no hay ritmo que proyectar
        ritmo_diario = unidades_vendidas / VENTANA_RITMO_VENTAS
        dias_restantes = producto.stock_actual / ritmo_diario
        if dias_restantes < UMBRAL_DIAS_STOCK:
            productos_criticos.append({
                'nombre': producto.nombre,
                'stock_actual': producto.stock_actual,
                'dias_restantes': round(dias_restantes, 1),
            })
    productos_criticos.sort(key=lambda p: p['dias_restantes'])

    # -- productos sin producción registrada en la última semana --
    desde_produccion = hoy - timedelta(days=DIAS_SIN_PRODUCCION - 1)
    ids_con_produccion = (
        Produccion.objects
        .filter(fecha_produccion__date__gte=desde_produccion)
        .values_list('producto_id', flat=True)
    )
    productos_sin_produccion = list(
        productos_activos.exclude(id__in=ids_con_produccion).values_list('nombre', flat=True)
    )

    return productos_criticos, productos_sin_produccion


def _construir_contexto_periodo(desde, hasta):
    """Arma KPIs, top productos y datos de gráficos para un período dado.
    Se reutiliza en la vista HTML y en el PDF, para que ambos siempre
    muestren los mismos números."""
    producciones_periodo = Produccion.objects.filter(
        fecha_produccion__date__gte=desde,
        fecha_produccion__date__lte=hasta,
    ).order_by('-fecha_produccion')

    agregados = producciones_periodo.aggregate(total=Sum('cantidad_producida'), cantidad=Count('id'))
    total_producido = agregados['total'] or 0
    cantidad_producciones = agregados['cantidad'] or 0
    promedio_produccion = (total_producido / cantidad_producciones) if cantidad_producciones else 0

    top_productos = list(
        producciones_periodo.values('producto__nombre')
        .annotate(unidades=Sum('cantidad_producida'))
        .order_by('-unidades')[:5]
    )
    producto_top = top_productos[0]['producto__nombre'] if top_productos else None

    # -- línea: cantidad de producciones registradas por día --
    por_dia = (
        producciones_periodo
        .annotate(dia=TruncDate('fecha_produccion'))
        .values('dia')
        .annotate(cantidad=Count('id'))
        .order_by('dia')
    )
    etiquetas_conteo = [d['dia'].strftime('%d/%m') for d in por_dia]
    valores_conteo = [d['cantidad'] for d in por_dia]

    # -- barra apilada: unidades producidas por producto, por semana --
    por_semana_producto = (
        producciones_periodo
        .annotate(semana=TruncWeek('fecha_produccion'))
        .values('semana', 'producto__nombre')
        .annotate(unidades=Sum('cantidad_producida'))
        .order_by('semana')
    )

    semanas = sorted({fila['semana'] for fila in por_semana_producto})
    nombres_top = [p['producto__nombre'] for p in top_productos]  # el resto se agrupa en "Otros"

    datos_por_producto = {nombre: [0] * len(semanas) for nombre in nombres_top}
    datos_otros = [0] * len(semanas)
    indice_semana = {semana: i for i, semana in enumerate(semanas)}

    for fila in por_semana_producto:
        i = indice_semana[fila['semana']]
        nombre = fila['producto__nombre']
        if nombre in datos_por_producto:
            datos_por_producto[nombre][i] += fila['unidades']
        else:
            datos_otros[i] += fila['unidades']

    series_apiladas = [{'name': nombre, 'data': datos} for nombre, datos in datos_por_producto.items()]
    if any(datos_otros):
        series_apiladas.append({'name': 'Otros', 'data': datos_otros})

    etiquetas_semanas = [s.strftime('%d/%m') for s in semanas]

    return {
        'total_producido': total_producido,
        'cantidad_producciones': cantidad_producciones,
        'promedio_produccion': promedio_produccion,
        'producto_top': producto_top,
        'top_productos_producidos': top_productos,
        'etiquetas_conteo_json': json.dumps(etiquetas_conteo),
        'valores_conteo_json': json.dumps(valores_conteo),
        'etiquetas_semanas_json': json.dumps(etiquetas_semanas),
        'series_apiladas_json': json.dumps(series_apiladas),
    }


def listar_producciones(request):
    filtro, desde, hasta = _resolver_periodo(request)

    producciones_periodo = Produccion.objects.filter(
        fecha_produccion__date__gte=desde,
        fecha_produccion__date__lte=hasta,
    ).select_related('producto').order_by('-fecha_produccion')

    paginator = Paginator(producciones_periodo, 6)
    producciones = paginator.get_page(request.GET.get('page'))

    productos_criticos, productos_sin_produccion = _calcular_alertas()
    formulario = ImportarProduccionForm()

    contexto = {
        'producciones': producciones,
        'filtro': filtro,
        'desde': desde,
        'hasta': hasta,
        'productos_criticos': productos_criticos,
        'productos_sin_produccion': productos_sin_produccion,
        'formulario': formulario,
        **_construir_contexto_periodo(desde, hasta),
    }
    return render(request, 'listpc.html', contexto)


def crear_produccion(request):
    if request.method == 'POST':
        form = ProduccionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listar_producciones')
    else:
        form = ProduccionForm()

    return render(request, 'formpc.html', {'form': form})

def importar_produccion(request):
    if request.method == 'POST':
        formulario = ImportarProduccionForm(request.POST, request.FILES)
        if formulario.is_valid():
            archivo = request.FILES['archivo']
            try:
                libro = load_workbook(archivo, data_only=True)
            except Exception:
                messages.error(request, 'El archivo no es un Excel válido.')
                return redirect('importar_produccion')

            hoja = libro.active
            ids_nuevos = []
            omitidos = 0
            no_encontrados = []

            for fila in hoja.iter_rows(min_row=2, values_only=True):
                if not fila or not fila[0]:
                    continue

                nombre_producto = str(fila[0]).strip()
                cantidad = fila[1] if len(fila) > 1 else None
                observacion = fila[2] if len(fila) > 2 else None

                if not cantidad or cantidad <= 0:
                    omitidos += 1
                    continue

                try:
                    producto = Producto.objects.get(nombre__iexact=nombre_producto)
                except Producto.DoesNotExist:
                    no_encontrados.append(nombre_producto)
                    continue

                # .create() dispara el save() del modelo, que ya suma
                # automáticamente la cantidad al stock_actual del producto.
                produccion = Produccion.objects.create(
                    producto=producto,
                    cantidad_producida=cantidad,
                    observacion=observacion,
                )
                ids_nuevos.append(produccion.id)

            request.session['producciones_importadas_ids'] = ids_nuevos

            if no_encontrados:
                messages.warning(request, f'No se encontraron estos productos, se omitieron sus filas: {", ".join(no_encontrados)}')
            if omitidos:
                messages.warning(request, f'{omitidos} filas se omitieron por no tener una cantidad válida.')
            if ids_nuevos:
                messages.success(request, f'Se registraron {len(ids_nuevos)} producciones correctamente.')

            return redirect('producciones_importadas')
    else:
        formulario = ImportarProduccionForm()

    return render(request, 'listpc.html', {'formulario': formulario})


def producciones_importadas(request):
    ids = request.session.get('producciones_importadas_ids', [])
    producciones = Produccion.objects.filter(id__in=ids).select_related('producto').order_by('-fecha_produccion')
    return render(request, 'producciones_importadas.html', {'producciones': producciones})