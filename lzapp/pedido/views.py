from datetime import timedelta

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from dashboard.models import (
    Pedido, PerfilEmple, Notificacion, SugerenciaSistema, obtener_configuracion_entrega,
)
from pedido.services import obtener_distancia_km, obtener_ruta_completa
from pedido.asignacion import (
    asignar_pendientes_a, calcular_eta, carga_actual, procesar_pedidos_listos,
    recompactar_ruta,
)
from pedido.sugerencias import aplicar_sugerencia, generar_sugerencias
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
    """El repartidor reporta su posición actual — al arrancar a repartir no
    hace falta que ya tenga entregas asignadas: es justamente esta
    ubicación la que lo vuelve candidato para el motor de asignación.
    (Antes esto exigía una entrega activa para aceptar la ubicación, lo
    cual era un candado circular: nunca se le podía asignar una primera
    entrega a nadie porque nadie tenía coordenadas todavía.)

    Apenas se registra la posición se le carga la cola pendiente: si se
    acumularon pedidos ya preparados porque no había nadie repartiendo, el
    que arranca se lleva varios de una sola salida.
    """
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

    # Primero la cola: los pedidos que toma acá entran al bucle de abajo
    # ya con su ruta y su puesto, sin esperar al siguiente ping.
    asignados = asignar_pendientes_a(perfil_emple)

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
            # El tiempo que ve el cliente no es solo el trayecto: suma la
            # espera por las entregas que van antes en la ruta y la demora
            # extra si hay una incidencia reportada.
            pedido.tiempo_estimado_min = calcular_eta(
                tiempo_min, pedido.orden_en_ruta, pedido.minutos_extra_incidencia,
            )
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

    return JsonResponse({'ok': True, 'entregas_asignadas': asignados})

def _serializar_pedidos_tiempo_real(pedidos):
    """Arma el mismo JSON de seguimiento en vivo (posición del repartidor,
    destino del cliente, ruta) para cualquier queryset de Pedido ya filtrado
    — lo reutilizan el panel admin, el seguimiento del cliente y el mapa
    del repartidor, cada uno con su propio alcance de datos."""
    lista = []
    for ped in pedidos:
        venta = ped.venta
        detalles = list(venta.detalles.all())
        n_items = sum(d.cantidad for d in detalles)

        perfil_repartidor = getattr(ped.repartidor, 'perfilemple', None) if ped.repartidor else None

        # Cadena de respaldo para el destino: lo que se guardó en el
        # pedido, si no la dirección del perfil del cliente y, si tampoco
        # hay, las coordenadas. Decir "sin dirección" teniendo el pin
        # puesto es falso y deja al repartidor creyendo que no sabe a
        # dónde va.
        perfil_cliente = getattr(venta.usuario, 'perfil', None)
        direccion = ped.direccion_entrega or getattr(perfil_cliente, 'direccion', None)
        if not direccion and ped.cliente_latitud and ped.cliente_longitud:
            direccion = f'Ubicación marcada en el mapa ({ped.cliente_latitud}, {ped.cliente_longitud})'

        lista.append({
            'id': venta.id,
            'pedido_id': ped.id,
            'cliente': venta.usuario.get_full_name() or venta.usuario.username,
            'fecha': timezone.localtime(venta.fecha).strftime('%d/%m %H:%M'),
            # La versión legible no sirve para ordenar: no lleva el año, así
            # que un 31/12 quedaría siempre por encima de un 01/01 posterior.
            'fecha_iso': venta.fecha.isoformat(),
            'total': float(venta.total),
            'estado': ped.estado,
            'estado_display': ped.get_estado_display(),
            'repartidor': (ped.repartidor.get_full_name() or ped.repartidor.username) if ped.repartidor else None,
            'items': n_items,
            # Qué tiene que entregar, con cantidades. Sin esto el
            # repartidor llega a la puerta sin saber qué le lleva al
            # cliente, que es justamente el trabajo.
            'productos': [
                {
                    'nombre': d.producto.nombre,
                    'cantidad': d.cantidad,
                    # La foto ayuda a que el repartidor identifique el
                    # producto de un vistazo sin leer nombres parecidos.
                    'imagen': d.producto.imagen.url if d.producto.imagen else None,
                }
                for d in detalles
            ],
            'incidencia': ped.incidencia,
            'minutos_extra_incidencia': ped.minutos_extra_incidencia,
            'codigo_entrega': ped.codigo_entrega,
            'direccion_entrega': direccion,
            'cliente_latitud': float(ped.cliente_latitud) if ped.cliente_latitud else None,
            'cliente_longitud': float(ped.cliente_longitud) if ped.cliente_longitud else None,
            'repartidor_latitud': float(perfil_repartidor.repartidor_latitud) if perfil_repartidor and perfil_repartidor.repartidor_latitud else None,
            'repartidor_longitud': float(perfil_repartidor.repartidor_longitud) if perfil_repartidor and perfil_repartidor.repartidor_longitud else None,
            'distancia_km': float(ped.distancia_km) if ped.distancia_km else None,
            'tiempo_estimado_min': ped.tiempo_estimado_min,
            'ruta_polyline': ped.ruta_polyline,
            # Puesto en la ruta del repartidor: el cliente lo ve como
            # "hay N entregas antes de la tuya", que es lo que explica que
            # su tiempo estimado sea mayor que el trayecto puro.
            'orden_en_ruta': ped.orden_en_ruta,
            'pedidos_antes': (max((ped.orden_en_ruta or 1) - 1, 0)
                              if ped.estado == Pedido.Estado.EN_CAMINO else 0),
        })
    return lista


@vista_dashboard
def api_pedidos_tiempo_real(request):
    """Estado en vivo de los últimos pedidos: repartidor asignado y avance
    de la entrega, más lo que el sistema le sugiere ajustar al admin.

    Este endpoint es además uno de los que empujan el motor: el panel lo
    consulta cada 10 s, así que los pedidos que ya terminaron su
    preparación avanzan solos sin que nadie toque nada.
    """
    procesar_pedidos_listos()

    pedidos = (Pedido.objects
               .select_related('venta', 'venta__usuario', 'venta__usuario__perfil', 'repartidor', 'repartidor__perfilemple')
               .prefetch_related('venta__detalles__producto')
               .order_by('-fecha_creacion')[:20])

    lista = _serializar_pedidos_tiempo_real(pedidos)

    resumen = {
        'preparando': sum(1 for p in lista if p['estado'] == 'preparando'),
        'pendientes': sum(1 for p in lista if p['estado'] == 'pendiente'),
        'en_camino': sum(1 for p in lista if p['estado'] == 'en_camino'),
        'entregados': sum(1 for p in lista if p['estado'] == 'entregado'),
        'cancelados': sum(1 for p in lista if p['estado'] == 'cancelado'),
    }

    config = obtener_configuracion_entrega()
    sugerencias = [{
        'id': s.id,
        'tipo': s.tipo,
        'tipo_display': s.get_tipo_display(),
        'mensaje': s.mensaje,
        'valor_actual': s.valor_actual,
        'valor_sugerido': s.valor_sugerido,
        'muestras': s.muestras,
    } for s in generar_sugerencias()]

    return JsonResponse({
        'pedidos': lista,
        'resumen': resumen,
        'sugerencias': sugerencias,
        'minutos_preparacion': config.minutos_preparacion,
        'minutos_por_parada': config.minutos_por_parada,
        'max_pedidos_por_repartidor': config.max_pedidos_por_repartidor,
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
    procesar_pedidos_listos()

    # Activos + los que se cerraron hace poco: así, cuando el pedido se
    # entrega o se cancela, el cliente ve el estado final en vivo en vez
    # de que la página tenga que recargarse para enterarse.
    activos = Q(estado__in=['pendiente', 'preparando', 'en_camino'])
    recien_cerrados = Q(
        estado__in=['entregado', 'cancelado'],
        fecha_actualizacion__gte=timezone.now() - timedelta(minutes=30),
    )

    pedidos = (Pedido.objects
               .filter(venta__usuario=request.user)
               .filter(activos | recien_cerrados)
               .select_related('venta', 'venta__usuario', 'venta__usuario__perfil', 'repartidor', 'repartidor__perfilemple')
               .prefetch_related('venta__detalles__producto')
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

    procesar_pedidos_listos()

    pedidos = (Pedido.objects
               .filter(repartidor=request.user, estado__in=['preparando', 'en_camino'])
               .select_related('venta', 'venta__usuario', 'venta__usuario__perfil', 'repartidor', 'repartidor__perfilemple')
               .prefetch_related('venta__detalles__producto')
               # En el orden en que las tiene que hacer, no por fecha: ahora
               # lleva varias entregas en la misma salida.
               .order_by('orden_en_ruta', 'fecha_creacion'))

    perfil_emple.refresh_from_db()
    carga = carga_actual(request.user)

    return JsonResponse({
        'pedidos': _serializar_pedidos_tiempo_real(pedidos),
        'minutos_preparacion': obtener_configuracion_entrega().minutos_preparacion,
        # Su propio estado de turno y de carga: es lo que le dice cuánto
        # más le pueden asignar antes de que no le quepa nada.
        'repartidor': {
            'disponible': perfil_emple.disponible,
            'vehiculo': perfil_emple.vehiculo,
            'vehiculo_display': perfil_emple.get_vehiculo_display(),
            'capacidad_productos': perfil_emple.capacidad_productos,
            'carga_actual': carga,
            'cupo_libre': max(perfil_emple.capacidad_productos - carga, 0),
        },
    })

@login_required
@require_POST
def cancelar_pedido(request, pedido_id):
    """Cancelar es lo único que el admin sigue decidiendo a mano.

    El avance normal del pedido (preparando → pendiente → en camino →
    entregado) lo maneja el motor con los tiempos reales; dejarlo también
    en un selector manual era lo que permitía saltarse etapas y dejar
    pedidos sin repartidor para siempre. Cancelar, en cambio, es una
    excepción que el sistema no puede deducir solo.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    pedido = Pedido.objects.select_related('repartidor').filter(id=pedido_id).first()
    if not pedido:
        return JsonResponse({'error': 'Pedido no encontrado'}, status=404)

    if pedido.estado == Pedido.Estado.ENTREGADO:
        return JsonResponse({'error': 'Un pedido entregado ya no se puede cancelar'}, status=400)

    repartidor = pedido.repartidor
    pedido.estado = Pedido.Estado.CANCELADO
    pedido.orden_en_ruta = None
    pedido.save(update_fields=['estado', 'orden_en_ruta'])

    # El pedido sale de la ruta: los que quedan suben un puesto.
    if repartidor:
        recompactar_ruta(repartidor)

    return JsonResponse({'ok': True})


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
    pedido.orden_en_ruta = None
    pedido.save(update_fields=['estado', 'orden_en_ruta'])

    # Los pedidos que quedan en la ruta suben un puesto: sin esto el
    # siguiente cliente seguiría viendo "hay 1 entrega antes de la tuya"
    # cuando ya es el próximo.
    recompactar_ruta(request.user)

    # Se liberó cupo: si hay pedidos esperando en la cola, se los lleva.
    perfil_emple = PerfilEmple.objects.filter(empleado=request.user, rol='empleado').first()
    if perfil_emple:
        asignar_pendientes_a(perfil_emple)

    return JsonResponse({'ok': True})


@login_required
def mi_vehiculo(request):
    """Módulo propio del dashboard para registrar el vehículo de reparto.

    Vive aparte del mapa a propósito: es configuración que se registra una
    vez (o cuando se cambia de vehículo), no algo que se toque a mitad de
    una entrega. Lo que se guarda acá define cuánto puede cargar y, por lo
    tanto, qué pedidos le puede asignar el motor.
    """
    perfil_emple = PerfilEmple.objects.filter(empleado=request.user, rol='empleado').first()
    if not perfil_emple:
        messages.error(request, 'No tienes acceso a esta sección.')
        return redirect('Inicio_dash')

    entregas_activas = Pedido.objects.filter(
        repartidor=request.user, estado=Pedido.Estado.EN_CAMINO,
    ).count()

    return render(request, 'mi_vehiculo.html', {
        'perfil_emple': perfil_emple,
        'carga_actual': carga_actual(request.user),
        'entregas_activas': entregas_activas,
        'vehiculos': PerfilEmple.Vehiculo.choices,
    })


@login_required
@require_POST
def cambiar_estado_reparto(request):
    """El repartidor entra o sale de turno.

    Es lo único que lo vuelve candidato para el motor: antes `disponible`
    venía encendido de fábrica y el sistema le asignaba entregas a gente
    que ni había salido de su casa. Ahora nadie recibe nada hasta que
    aprieta "Empezar a repartir".
    """
    perfil_emple = PerfilEmple.objects.filter(empleado=request.user, rol='empleado').first()
    if not perfil_emple:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    activo = request.POST.get('activo') == '1'
    perfil_emple.disponible = activo
    perfil_emple.save(update_fields=['disponible'])

    asignados = 0
    if activo:
        activas = Q(repartidor=request.user, estado=Pedido.Estado.EN_CAMINO)
        antes = Pedido.objects.filter(activas).count()

        # Dos barridos: los que ya terminaron su preparación (y que nadie
        # despachó porque no había repartidor en turno) y la cola que venía
        # esperando. Con solo el segundo, un pedido listo hace un rato se
        # quedaba afuera hasta el siguiente refresco de algún panel.
        procesar_pedidos_listos()
        asignar_pendientes_a(perfil_emple)

        asignados = Pedido.objects.filter(activas).count() - antes

    return JsonResponse({
        'ok': True,
        'disponible': perfil_emple.disponible,
        'entregas_asignadas': max(asignados, 0),
    })


@login_required
@require_POST
def actualizar_vehiculo(request):
    """Con qué reparte y cuánto le cabe: define qué se le puede asignar."""
    perfil_emple = PerfilEmple.objects.filter(empleado=request.user, rol='empleado').first()
    if not perfil_emple:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    vehiculo = request.POST.get('vehiculo')
    if vehiculo not in PerfilEmple.Vehiculo.values:
        return JsonResponse({'error': 'Vehículo inválido'}, status=400)

    capacidad, error = leer_entero_acotado(
        request.POST.get('capacidad_productos'), 1, 500, 'La capacidad'
    )
    if error:
        return JsonResponse({'error': error}, status=400)

    perfil_emple.vehiculo = vehiculo
    perfil_emple.capacidad_productos = capacidad
    perfil_emple.save(update_fields=['vehiculo', 'capacidad_productos'])

    return JsonResponse({
        'ok': True,
        'vehiculo': perfil_emple.vehiculo,
        'vehiculo_display': perfil_emple.get_vehiculo_display(),
        'capacidad_productos': perfil_emple.capacidad_productos,
    })


@login_required
@require_POST
def reportar_incidencia(request, pedido_id):
    """El repartidor reporta una novedad de SU entrega.

    La incidencia pasó del admin al repartidor: es el que está en la
    calle y el único que sabe de verdad si hay trancón, si el cliente no
    contesta o si la dirección no existe. El admin se entera por
    notificación, no teniendo que adivinarlo desde el panel.
    """
    pedido = (Pedido.objects
              .select_related('venta', 'venta__usuario')
              .filter(id=pedido_id, repartidor=request.user)
              .first())
    if not pedido:
        return JsonResponse({'error': 'No tienes esta entrega asignada'}, status=403)

    incidencia = (request.POST.get('incidencia') or '').strip()[:255]
    minutos_extra, error = leer_entero_acotado(
        request.POST.get('minutos_extra') or 0, 0, 600, 'La demora extra'
    )
    if error:
        return JsonResponse({'error': error}, status=400)

    hubo_cambio = incidencia and incidencia != (pedido.incidencia or '')

    # La demora reemplaza a la anterior (no se acumula sola), pero sí se
    # refleja de una en el tiempo que ve el cliente.
    base = (pedido.tiempo_estimado_min or 0) - pedido.minutos_extra_incidencia
    pedido.incidencia = incidencia or None
    pedido.minutos_extra_incidencia = minutos_extra
    pedido.tiempo_estimado_min = max(base, 0) + minutos_extra
    pedido.save(update_fields=['incidencia', 'minutos_extra_incidencia', 'tiempo_estimado_min'])

    if hubo_cambio:
        Notificacion.objects.create(
            usuario=pedido.venta.usuario,
            titulo='Novedad con tu pedido',
            mensaje=f'{pedido.incidencia} — Pedido #{pedido.id}',
            tipo='warning',
            url='/pedido/mi-pedido',
        )
        quien = request.user.get_full_name() or request.user.username
        for staff in User.objects.filter(is_staff=True, is_active=True):
            Notificacion.objects.create(
                usuario=staff,
                titulo='Incidencia reportada',
                mensaje=f'{quien} reportó en el pedido #{pedido.id}: {pedido.incidencia}',
                tipo='warning',
                url='/pedido/Pedidos',
            )

    return JsonResponse({
        'ok': True,
        'incidencia': pedido.incidencia,
        'minutos_extra': pedido.minutos_extra_incidencia,
        'tiempo_estimado_min': pedido.tiempo_estimado_min,
    })


def service_worker_entregas(request):
    """Service worker del panel del repartidor, servido desde la raíz.

    Tiene que salir de la raíz del sitio y no de /static/ porque un
    service worker solo controla páginas que cuelguen de su propia ruta:
    desde /static/pedido/js/ no podría controlar /pedido/mis-entregas.
    """
    return render(request, 'pedido/sw_entregas.js', content_type='application/javascript')


@vista_dashboard
@require_POST
def resolver_sugerencia(request, sugerencia_id):
    """El admin aplica o descarta lo que el sistema le propuso.

    Aplicar guarda el valor recomendado en la configuración del negocio;
    descartar la silencia por un día para no volver a insistir con el
    mismo patrón en el siguiente refresco del panel.
    """
    sugerencia = SugerenciaSistema.objects.filter(
        id=sugerencia_id, estado=SugerenciaSistema.Estado.PENDIENTE,
    ).first()
    if not sugerencia:
        return JsonResponse({'error': 'Esa sugerencia ya no está vigente'}, status=404)

    accion = request.POST.get('accion')
    if accion == 'aplicar':
        config = aplicar_sugerencia(sugerencia)
        return JsonResponse({
            'ok': True,
            'minutos_preparacion': config.minutos_preparacion,
            'minutos_por_parada': config.minutos_por_parada,
        })

    if accion == 'descartar':
        sugerencia.estado = SugerenciaSistema.Estado.DESCARTADA
        sugerencia.save(update_fields=['estado'])
        return JsonResponse({'ok': True})

    return JsonResponse({'error': 'Acción inválida'}, status=400)