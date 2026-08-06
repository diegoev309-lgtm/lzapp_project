from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from weasyprint import HTML
from django.template.loader import render_to_string
from django.http import HttpResponse

from dashboard.models import Producto, CampanaDescuento, DescuentoAsignado, TiradaDiaria
from .forms import CampanaDescuentoForm
from .services import (
    previsualizar_campana, obtener_badges_vencimiento_productos,
    jugar_ruleta_del_dia, reclamar_premio_dia,
)


#@login_required
#@permission_required('descuentos.view_campanadescuento', raise_exception=True)
def panel_descuentos(request):
    query = request.GET.get('q', '').strip()

    # Igual que en el panel de productos: orden fijo + paginado, para no
    # tener que escrollear cuando hay muchos productos.
    productos_qs = Producto.objects.all().order_by('-id')
    if query:
        productos_qs = productos_qs.filter(nombre__icontains=query)

    paginator = Paginator(productos_qs, 5)
    productos = paginator.get_page(request.GET.get('page'))

    ahora = timezone.now()
    # Las anotaciones (campañas activas, premios vigentes) se calculan solo
    # sobre la página actual, no sobre todo el queryset, para no cargar de
    # más cuando hay muchos productos.
    for p in productos:
        campanas_del_producto = CampanaDescuento.objects.filter(productos=p, activo=True)
        p.campanas_activas_count = campanas_del_producto.count()
        p.tiene_campana_activa = p.campanas_activas_count > 0
        p.premios_activos_count = DescuentoAsignado.objects.filter(
            producto=p, usado=False, fecha_expiracion__gte=ahora
        ).count()

    campanas_qs = CampanaDescuento.objects.all().order_by('-fecha_creacion')
    if query:
        campanas_qs = campanas_qs.filter(
            Q(nombre__icontains=query) | Q(productos__nombre__icontains=query)
        ).distinct()

    # Página aparte para campañas (page_campanas) para que no choque con
    # la paginación de productos (page), ya que ambas viven en la misma URL.
    paginator_campanas = Paginator(campanas_qs, 4)
    campanas = paginator_campanas.get_page(request.GET.get('page_campanas'))

    for c in campanas:
        resultado = previsualizar_campana(c)
        if 'detalle' in resultado:
            c.preview_clientes = sum(item['clientes_que_recibiran_el_premio'] for item in resultado['detalle'])
        else:
            c.preview_clientes = 0

    return render(request, 'listdes.html', {
        'productos': productos,
        'campanas': campanas,
        'query': query,
    })


#@login_required
#@permission_required('descuentos.add_campanadescuento', raise_exception=True)
def crear_campana_descuento(request):
    if request.method == 'POST':
        form = CampanaDescuentoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Campaña creada correctamente.')
            return redirect('panel_descuentos')
    else:
        form = CampanaDescuentoForm()
    return render(request, 'formdes.html', {
        'form': form,
        'modo': 'crear',
        'productos_badges': obtener_badges_vencimiento_productos(),
    })


#@login_required
#@permission_required('descuentos.change_campanadescuento', raise_exception=True)
def editar_campana_descuento(request, pk):
    campana = get_object_or_404(CampanaDescuento, pk=pk)
    if request.method == 'POST':
        form = CampanaDescuentoForm(request.POST, instance=campana)
        if form.is_valid():
            form.save()
            messages.success(request, 'Campaña actualizada.')
            return redirect('panel_descuentos')
    else:
        form = CampanaDescuentoForm(instance=campana)
    return render(request, 'formdes.html', {
        'form': form,
        'modo': 'editar',
        'campana': campana,
        'productos_badges': obtener_badges_vencimiento_productos(),
    })


#@login_required
#@permission_required('descuentos.delete_campanadescuento', raise_exception=True)
def eliminar_campana_descuento(request, pk):
    campana = get_object_or_404(CampanaDescuento, pk=pk)
    if request.method == 'POST':
        campana.delete()
        messages.success(request, 'Campaña eliminada.')
        return redirect('panel_descuentos')
    return render(request, 'deletedes.html', {'campana': campana})


#@login_required
#@permission_required('descuentos.change_campanadescuento', raise_exception=True)
def toggle_campana_descuento(request, pk):
    """Activa/desactiva la campaña con un solo clic (botón del panel)."""
    campana = get_object_or_404(CampanaDescuento, pk=pk)
    if request.method == 'POST':
        campana.activo = not campana.activo
        campana.save(update_fields=['activo'])
        estado = 'activada' if campana.activo else 'desactivada'
        messages.success(request, f'Campaña {estado}.')
    return redirect('panel_descuentos')


#@login_required
#@permission_required('descuentos.view_campanadescuento', raise_exception=True)
def previsualizar_producto(request, pk):
    """
    Endpoint JSON (consumido por fetch() desde el modal del panel):
    muestra, sin ejecutar nada, a cuántos clientes aplicaría cada
    campaña activa que incluye este producto (stock + % + tope).
    """
    producto = get_object_or_404(Producto, pk=pk)
    campanas = CampanaDescuento.objects.filter(productos=producto, activo=True)

    previsualizaciones = []
    for c in campanas:
        resultado = previsualizar_campana(c)
        # quitamos ids_elegibles: son datos internos (IDs de usuarios),
        # no hace falta ni conviene mandarlos al navegador
        if 'detalle' in resultado:
            for item in resultado['detalle']:
                item.pop('ids_elegibles', None)
        previsualizaciones.append(resultado)

    return JsonResponse({'producto': producto.nombre, 'previsualizaciones': previsualizaciones})


def marcar_premio_mostrado(request):
    """
    Llamado por el JS del home justo después de que termina la animación
    de "¡Felicidades!". Marca ese premio como ya mostrado para que, si el
    cliente recarga la página, no le vuelva a salir la animación desde
    cero (pero el premio sigue activo/usable hasta que se use o expire).
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'metodo no permitido'}, status=405)

    codigo = request.POST.get('codigo', '').strip()
    actualizados = DescuentoAsignado.objects.filter(
        usuario=request.user, codigo=codigo, mostrado=False
    ).update(mostrado=True)

    return JsonResponse({'ok': True, 'actualizado': bool(actualizados)})


def generar_pdf_descuentos(request):
    campanas = (
        CampanaDescuento.objects
        .all()
        .prefetch_related('productos')
        .order_by('-activo', 'nombre')
    )

    contexto = {
        'campanas': campanas,
        'total_campanas': campanas.count(),
        'campanas_activas': campanas.filter(activo=True).count(),
        'campanas_inactivas': campanas.filter(activo=False).count(),
        'fecha_generacion': timezone.now(),
    }

    html_string = render_to_string('reporte_descuentos.html', contexto)
    pdf_bytes = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_descuentos.pdf"'
    return response


def jugar_ruleta_dia(request):
    """
    Llamado por el fetch() del JS del home cuando el usuario ya tocó los
    3 quesos y le da a "¡Sortear la oferta del día!" en el modo del
    juego diario (todos pueden jugar, registrados y anónimos). Devuelve
    el resultado para que el JS dispare la MISMA animación que ya existe
    (mostrarNumeroConGiro / mostrarFelicidades).
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'metodo no permitido'}, status=405)

    tirada, es_nueva = jugar_ruleta_del_dia(request)

    return JsonResponse({
        'ok': True,
        'ya_jugado': not es_nueva,
        'resultado': tirada.resultado,
        'resultado_texto': tirada.get_resultado_display(),
        'reclamado': tirada.reclamado,
        'fecha_expiracion': tirada.fecha_expiracion.isoformat(),
    })


def reclamar_premio_dia_ajax(request):
    """
    Llamado justo después de la animación de "¡Felicidades!" cuando el
    premio ganado es de la ruleta diaria (no de campaña oficial). Marca
    la tirada de hoy como reclamada y aplica su efecto (cupón/envío en
    sesión, o deja el boleto dorado listo para la próxima ejecución).
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'metodo no permitido'}, status=405)

    tirada, estado = reclamar_premio_dia(request)
    if tirada is None:
        return JsonResponse({'ok': False, 'error': estado}, status=400)

    return JsonResponse({
        'ok': estado == 'ok',
        'estado': estado,
        'resultado': tirada.resultado,
        'resultado_texto': tirada.get_resultado_display(),
        'reclamado': tirada.reclamado,
    })
