from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from dashboard.models import Pedido, PerfilEmple, Notificacion, obtener_configuracion_entrega
from pedido.services import obtener_distancia_km, obtener_ruta_completa
from seguridad.decorators import vista_dashboard
from seguridad.validators import leer_decimal_acotado, leer_entero_acotado

@vista_dashboard
def Pedidos(request):
    return render(request, 'pedidos.html')

@login_required
def mis_entregas(request):
    """Panel del repartidor: sus entregas activas y el control para compartir ubicación."""
    perfil_emple = PerfilEmple.objects.filter(empleado=request.user, rol='empleado').first()

    if not perfil_emple:
        messages.error(request, "No tienes acceso a esta sección.")
        return redirect('Inicio_dash')

    pedidos_activos = Pedido.objects.filter(
        repartidor=request.user,
        estado__in=['preparando', 'en_camino'],
    ).select_related('venta', 'venta__usuario').order_by('-fecha_creacion')

    return render(request, 'mis_entregas.html', {
        'pedidos_activos': pedidos_activos,
        'perfil_emple': perfil_emple,
    })


@login_required
@require_POST
def actualizar_ubicacion_repartidor(request):
    """El repartidor reporta su posición actual — mientras esté disponible,
    no hace falta que ya tenga un pedido activo asignado: es justamente
    esta ubicación la que usa asignar_repartidor_automatico() para poder
    elegirlo como candidato en el próximo pedido que entre a 'preparando'.
    (Antes esto exigía una entrega activa para aceptar la ubicación, lo
    cual era un candado circular: nunca se le podía asignar una primera
    entrega a nadie porque nadie tenía coordenadas todavía.)"""
    perfil_emple = PerfilEmple.objects.filter(empleado=request.user, rol='empleado').first()
    if not perfil_emple:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    lat_raw = request.POST.get('latitud')
    lng_raw = request.POST.get('longitud')
    if not lat_raw or not lng_raw:
        return JsonResponse({'error': 'Faltan coordenadas'}, status=400)

    lat, error_lat = leer_decimal_acotado(lat_raw, -90, 90, 'La latitud')
    lng, error_lng = leer_decimal_acotado(lng_raw, -180, 180, 'La longitud')
    if error_lat or error_lng:
        return JsonResponse({'error': error_lat or error_lng}, status=400)

    perfil_emple.repartidor_latitud = lat
    perfil_emple.repartidor_longitud = lng
    perfil_emple.ubicacion_actualizada = timezone.now()
    perfil_emple.save(update_fields=['repartidor_latitud', 'repartidor_longitud', 'ubicacion_actualizada'])

    pedidos_activos = Pedido.objects.filter(
        repartidor=request.user,
        estado__in=['preparando', 'en_camino'],
        cliente_latitud__isnull=False,
    ).select_related('venta', 'venta__usuario')

    for pedido in pedidos_activos:
        campos = []

        # La ruta se pide una sola vez por pedido: es el caso del pedido
        # que se asignó cuando el repartidor todavía no compartía GPS, así
        # que recién ahora podemos trazar por dónde tiene que ir.
        if not pedido.ruta_polyline:
            distancia_km, tiempo_min, polyline = obtener_ruta_completa(
                lat, lng, pedido.cliente_latitud, pedido.cliente_longitud
            )
            pedido.ruta_polyline = polyline
            campos.append('ruta_polyline')
        else:
            distancia_km, tiempo_min = obtener_distancia_km(
                lat, lng, pedido.cliente_latitud, pedido.cliente_longitud
            )

        if distancia_km is not None:
            pedido.distancia_km = round(distancia_km, 2)
            campos.append('distancia_km')
        if tiempo_min is not None:
            # Si el admin registró una incidencia, el tiempo que ve el
            # cliente incluye la demora extra de esa incidencia.
            pedido.tiempo_estimado_min = tiempo_min + pedido.minutos_extra_incidencia
            campos.append('tiempo_estimado_min')

        if (pedido.estado == 'en_camino'
                and not pedido.notificado_proximidad
                and distancia_km is not None
                and distancia_km <= 1):  # menos de 1 km = "está por llegar"
            Notificacion.objects.create(
                usuario=pedido.venta.usuario,
                titulo='Tu pedido está cerca',
                mensaje=f'El repartidor está a menos de 1 km — Pedido #{pedido.id} 📍',
                tipo='info',
            )
            pedido.notificado_proximidad = True
            campos.append('notificado_proximidad')

        if campos:
            pedido.save(update_fields=campos)

    return JsonResponse({'ok': True})

def _serializar_pedidos_tiempo_real(pedidos):
    """Arma el mismo JSON de seguimiento en vivo (posición del repartidor,
    destino del cliente, ruta) para cualquier queryset de Pedido ya filtrado
    — lo reutilizan el panel admin, el seguimiento del cliente y el mapa
    del repartidor, cada uno con su propio alcance de datos."""
    lista = []
    for ped in pedidos:
        venta = ped.venta
        n_items = sum(d.cantidad for d in venta.detalles.all())

        perfil_repartidor = getattr(ped.repartidor, 'perfilemple', None) if ped.repartidor else None

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
            'minutos_extra_incidencia': ped.minutos_extra_incidencia,
            'codigo_entrega': ped.codigo_entrega,
            'direccion_entrega': ped.direccion_entrega,
            'cliente_latitud': float(ped.cliente_latitud) if ped.cliente_latitud else None,
            'cliente_longitud': float(ped.cliente_longitud) if ped.cliente_longitud else None,
            'repartidor_latitud': float(perfil_repartidor.repartidor_latitud) if perfil_repartidor and perfil_repartidor.repartidor_latitud else None,
            'repartidor_longitud': float(perfil_repartidor.repartidor_longitud) if perfil_repartidor and perfil_repartidor.repartidor_longitud else None,
            'distancia_km': float(ped.distancia_km) if ped.distancia_km else None,
            'tiempo_estimado_min': ped.tiempo_estimado_min,
            'ruta_polyline': ped.ruta_polyline,
        })
    return lista


@vista_dashboard
def api_pedidos_tiempo_real(request):
    """Estado en vivo de los últimos pedidos: repartidor asignado y avance de la entrega."""
    pedidos = (Pedido.objects
               .select_related('venta', 'venta__usuario', 'repartidor', 'repartidor__perfilemple')
               .prefetch_related('venta__detalles')
               .order_by('-fecha_creacion')[:20])

    lista = _serializar_pedidos_tiempo_real(pedidos)

    resumen = {
        'pendientes': sum(1 for p in lista if p['estado'] in ('pendiente', 'preparando')),
        'en_camino': sum(1 for p in lista if p['estado'] == 'en_camino'),
        'entregados': sum(1 for p in lista if p['estado'] == 'entregado'),
        'cancelados': sum(1 for p in lista if p['estado'] == 'cancelado'),
    }

    return JsonResponse({
        'pedidos': lista,
        'resumen': resumen,
        'minutos_preparacion': obtener_configuracion_entrega().minutos_preparacion,
    })


@vista_dashboard
@require_POST
def actualizar_tiempo_preparacion(request):
    """Tiempo de preparación general del negocio (no por pedido): lo que
    tarda la cocina en dejar listo cualquier pedido. El admin lo ajusta
    según cómo venga el día y afecta a todos los pedidos nuevos."""
    minutos, error = leer_entero_acotado(
        request.POST.get('minutos_preparacion'), 1, 600, 'El tiempo de preparación'
    )
    if error:
        return JsonResponse({'error': error}, status=400)

    config = obtener_configuracion_entrega()
    config.minutos_preparacion = minutos
    config.save(update_fields=['minutos_preparacion'])

    return JsonResponse({'ok': True, 'minutos_preparacion': config.minutos_preparacion})


@login_required
def mi_pedido_seguimiento(request):
    """Página del cliente: seguimiento en vivo de su pedido activo más reciente."""
    pedido_activo = (Pedido.objects
                      .filter(venta__usuario=request.user, estado__in=['pendiente', 'preparando', 'en_camino'])
                      .select_related('venta')
                      .order_by('-fecha_creacion')
                      .first())
    return render(request, 'mi_pedido_seguimiento.html', {'pedido_activo': pedido_activo})


@login_required
def mi_pedido_tiempo_real(request):
    """Igual que api_pedidos_tiempo_real, pero acotado a los pedidos activos
    del cliente logueado — nunca expone pedidos ni ubicaciones ajenas."""
    pedidos = (Pedido.objects
               .filter(venta__usuario=request.user, estado__in=['pendiente', 'preparando', 'en_camino'])
               .select_related('venta', 'venta__usuario', 'repartidor', 'repartidor__perfilemple')
               .prefetch_related('venta__detalles')
               .order_by('-fecha_creacion'))

    return JsonResponse({
        'pedidos': _serializar_pedidos_tiempo_real(pedidos),
        'minutos_preparacion': obtener_configuracion_entrega().minutos_preparacion,
    })


@login_required
def mis_entregas_tiempo_real(request):
    """Igual que api_pedidos_tiempo_real, pero acotado a las entregas
    asignadas al repartidor logueado — para que vea en el mapa a dónde
    tiene que llevar cada pedido activo."""
    perfil_emple = PerfilEmple.objects.filter(empleado=request.user, rol='empleado').first()
    if not perfil_emple:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    pedidos = (Pedido.objects
               .filter(repartidor=request.user, estado__in=['preparando', 'en_camino'])
               .select_related('venta', 'venta__usuario', 'repartidor', 'repartidor__perfilemple')
               .prefetch_related('venta__detalles')
               .order_by('-fecha_creacion'))

    return JsonResponse({
        'pedidos': _serializar_pedidos_tiempo_real(pedidos),
        'minutos_preparacion': obtener_configuracion_entrega().minutos_preparacion,
    })

@login_required
@require_POST
def actualizar_entrega_pedido(request, pedido_id):
    """El admin ajusta el tiempo estimado y/o registra una incidencia.

    El tiempo se calcula solo con OSRM, pero el admin manda: puede
    sobreescribirlo a mano. Si registra una incidencia con demora, esos
    minutos quedan guardados aparte y se le suman al tiempo cada vez que
    se recalcula la ruta, en vez de perderse en el siguiente ping del GPS.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    pedido = Pedido.objects.select_related('venta', 'venta__usuario').filter(id=pedido_id).first()
    if not pedido:
        return JsonResponse({'error': 'Pedido no encontrado'}, status=404)

    campos = []
    incidencia_nueva = False

    if 'incidencia' in request.POST:
        incidencia = (request.POST.get('incidencia') or '').strip()[:255]
        incidencia_nueva = bool(incidencia) and incidencia != (pedido.incidencia or '')
        pedido.incidencia = incidencia or None
        campos.append('incidencia')

    if 'minutos_extra' in request.POST:
        minutos_extra, error = leer_entero_acotado(
            request.POST.get('minutos_extra'), 0, 600, 'La demora extra'
        )
        if error:
            return JsonResponse({'error': error}, status=400)

        # La demora extra reemplaza a la anterior (no se acumula sola), pero
        # sí se refleja en el tiempo que ve el cliente ahora mismo.
        base = (pedido.tiempo_estimado_min or 0) - pedido.minutos_extra_incidencia
        pedido.minutos_extra_incidencia = minutos_extra
        pedido.tiempo_estimado_min = max(base, 0) + minutos_extra
        campos += ['minutos_extra_incidencia', 'tiempo_estimado_min']

    if not campos:
        return JsonResponse({'error': 'No se envió nada para actualizar'}, status=400)

    pedido.save(update_fields=campos)

    if incidencia_nueva:
        Notificacion.objects.create(
            usuario=pedido.venta.usuario,
            titulo='Novedad con tu pedido',
            mensaje=f'{pedido.incidencia} — Pedido #{pedido.id}',
            tipo='warning',
            url='/pedido/mi-pedido',
        )

    return JsonResponse({
        'ok': True,
        'incidencia': pedido.incidencia,
        'minutos_extra': pedido.minutos_extra_incidencia,
        'tiempo_estimado_min': pedido.tiempo_estimado_min,
    })


@login_required
@require_POST
def actualizar_estado_pedido(request, pedido_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    nuevo_estado = request.POST.get('estado')
    if nuevo_estado not in dict(Pedido.Estado.choices):
        return JsonResponse({'error': 'Estado inválido'}, status=400)

    try:
        pedido = Pedido.objects.get(id=pedido_id)
    except Pedido.DoesNotExist:
        return JsonResponse({'error': 'Pedido no encontrado'}, status=404)

    pedido.estado = nuevo_estado
    pedido.save(update_fields=['estado'])

    return JsonResponse({
        'ok': True,
        'repartidor': (pedido.repartidor.get_full_name() or pedido.repartidor.username) if pedido.repartidor else None,
    })


@login_required
@require_POST
def confirmar_entrega_pedido(request, pedido_id):
    """El repartidor cierra la entrega escribiendo el PIN de 4 dígitos que
    el cliente le muestra en su pantalla. Es la única forma de pasar a
    'entregado' desde el lado del repartidor — así queda constancia de que
    entregó el pedido correcto a la persona correcta, no cualquiera."""
    pedido = (Pedido.objects
              .select_related('venta', 'venta__usuario')
              .filter(id=pedido_id, repartidor=request.user)
              .first())
    if not pedido:
        return JsonResponse({'error': 'No tienes esta entrega asignada'}, status=403)

    if pedido.estado != Pedido.Estado.EN_CAMINO:
        return JsonResponse({'error': 'Este pedido no está en camino'}, status=400)

    codigo = (request.POST.get('codigo') or '').strip()
    if not pedido.codigo_entrega or codigo != pedido.codigo_entrega:
        return JsonResponse({'error': 'Código incorrecto. Confírmalo con el cliente.'}, status=400)

    pedido.estado = Pedido.Estado.ENTREGADO
    pedido.save(update_fields=['estado'])

    return JsonResponse({'ok': True})