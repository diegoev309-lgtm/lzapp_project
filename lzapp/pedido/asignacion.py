"""Motor de asignación y avance automático de los pedidos.

El ciclo lo maneja el sistema, no el admin a mano:

    pago ─→ PREPARANDO ──(pasa el tiempo de preparación)──→ ¿hay repartidor con cupo?
                                                             │
                                       no ─→ PENDIENTE (cola de espera, ya preparado)
                                       sí ─→ EN_CAMINO (con su puesto en la ruta)

PENDIENTE es la cola *posterior* a la preparación, no un paso previo: la
producción arranca sola con el pago y nunca se queda esperando un clic.

Nada de esto necesita cron ni celery. El motor lo empujan los mismos
endpoints en vivo que el panel del admin, el seguimiento del cliente y el
panel del repartidor ya consultan cada 10 segundos (procesar_pedidos_listos),
más el momento en que un repartidor empieza a repartir (asignar_pendientes_a).

Un repartidor puede llevar varias entregas en la misma salida: hasta
config.max_pedidos_por_repartidor. Cada pedido guarda su `orden_en_ruta`
(1 = próxima parada) y su tiempo estimado ya incluye la espera por las
entregas que van antes, que es lo que el cliente ve como "hay N antes del
tuyo".
"""
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone

from dashboard.models import DetalleVenta, Pedido, PerfilEmple, obtener_configuracion_entrega
from .services import obtener_direccion, obtener_repartidor_mas_cercano, obtener_ruta_completa

# Cuánto vale la última posición GPS de un repartidor para considerarlo
# "en la calle". Más viejo que esto y no sirve para elegir al más cercano
# (pero el repartidor sigue siendo candidato por el plan B de carga).
MINUTOS_GPS_VIGENTE = 15


def unidades_de(pedido):
    """Cuántas unidades de producto tiene que cargar este pedido."""
    return DetalleVenta.objects.filter(venta_id=pedido.venta_id).aggregate(
        n=Sum('cantidad'))['n'] or 0


def carga_actual(empleado):
    """Unidades que el repartidor ya lleva encima en su ruta activa."""
    return DetalleVenta.objects.filter(
        venta__pedido__repartidor=empleado,
        venta__pedido__estado=Pedido.Estado.EN_CAMINO,
    ).aggregate(n=Sum('cantidad'))['n'] or 0


def _candidatos_con_cupo(config, unidades_necesarias=0):
    """Repartidores disponibles a los que todavía les cabe esta entrega.

    Dos topes: cuántos pedidos puede llevar a la vez (configuración del
    negocio) y cuántas unidades le caben en el vehículo (cada repartidor
    tiene la suya). El segundo es el que de verdad manda: no tiene sentido
    mandarle 30 quesos a alguien que reparte en bicicleta.
    """
    activas = Count(
        'empleado__entregas_asignadas',
        filter=Q(empleado__entregas_asignadas__estado=Pedido.Estado.EN_CAMINO),
    )
    candidatos = (PerfilEmple.objects
                  .filter(rol='empleado', disponible=True)
                  .select_related('empleado')
                  .annotate(entregas_activas=activas)
                  .filter(entregas_activas__lt=config.max_pedidos_por_repartidor)
                  .order_by('entregas_activas', 'id'))

    if not unidades_necesarias:
        return list(candidatos)

    # El cupo por unidades se filtra acá y no en SQL: son pocos
    # repartidores y la consulta anidada no compensa la complejidad.
    return [c for c in candidatos
            if carga_actual(c.empleado) + unidades_necesarias <= c.capacidad_productos]


def _elegir_repartidor(pedido, config):
    """El más cercano al cliente entre los que tienen GPS reciente; si
    ninguno lo tiene, el que menos entregas lleve encima.

    El plan B importa: sin él un pedido se quedaba trabado esperando que
    algún repartidor abriera la app y empezara a compartir ubicación.
    """
    candidatos = _candidatos_con_cupo(config, unidades_de(pedido))
    if not candidatos:
        return None

    if pedido.cliente_latitud and pedido.cliente_longitud:
        con_gps = [
            c for c in candidatos
            if c.repartidor_latitud and c.repartidor_longitud and c.ubicacion_actualizada
            and c.ubicacion_actualizada >= timezone.now() - timedelta(minutes=MINUTOS_GPS_VIGENTE)
        ]
        if con_gps:
            mejor, _distancia, _tiempo = obtener_repartidor_mas_cercano(
                pedido.cliente_latitud, pedido.cliente_longitud, con_gps
            )
            if mejor:
                return mejor

    return candidatos[0]


def calcular_eta(tiempo_viaje_min, orden_en_ruta, minutos_extra=0, config=None):
    """Tiempo que va a esperar el cliente, contando la cola.

    No es solo lo que tarda el trayecto: si su pedido es la parada #3, hay
    que sumarle lo que el repartidor tarda en las dos entregas anteriores
    (config.minutos_por_parada cada una). Sin esto el cliente ve un tiempo
    que se cumple para el primero de la ruta y se "atrasa" sin explicación
    para todos los demás.
    """
    if tiempo_viaje_min is None:
        return None

    config = config or obtener_configuracion_entrega()
    paradas_antes = max((orden_en_ruta or 1) - 1, 0)
    total = tiempo_viaje_min + paradas_antes * config.minutos_por_parada + (minutos_extra or 0)
    return int(round(total))


def _asignar(pedido, perfil, config):
    """Le entrega el pedido a ese repartidor y lo pone en camino."""
    activas = Pedido.objects.filter(
        repartidor=perfil.empleado, estado=Pedido.Estado.EN_CAMINO,
    ).count()

    pedido.repartidor = perfil.empleado
    pedido.orden_en_ruta = activas + 1
    pedido.estado = Pedido.Estado.EN_CAMINO
    campos = ['repartidor', 'orden_en_ruta', 'estado']

    # Si el pedido quedó solo con el pin (el cliente usó el GPS y la
    # geocodificación del navegador no respondió), se resuelve acá una
    # sola vez. Sin esto el repartidor ve "Sin dirección registrada"
    # aunque el destino esté bien puesto en el mapa.
    if not pedido.direccion_entrega and pedido.cliente_latitud and pedido.cliente_longitud:
        direccion = obtener_direccion(pedido.cliente_latitud, pedido.cliente_longitud)
        if direccion:
            pedido.direccion_entrega = direccion[:255]
            campos.append('direccion_entrega')

    # La geometría de la ruta se pide una sola vez por asignación (no en
    # cada ping de GPS): la misma respuesta trae distancia y tiempo.
    tiene_ruta = (pedido.cliente_latitud and pedido.cliente_longitud
                  and perfil.repartidor_latitud and perfil.repartidor_longitud)
    if tiene_ruta:
        distancia, tiempo, polyline = obtener_ruta_completa(
            perfil.repartidor_latitud, perfil.repartidor_longitud,
            pedido.cliente_latitud, pedido.cliente_longitud,
        )
        pedido.ruta_polyline = polyline
        pedido.distancia_km = round(distancia, 2) if distancia is not None else None
        pedido.tiempo_estimado_min = calcular_eta(
            tiempo, pedido.orden_en_ruta, pedido.minutos_extra_incidencia, config,
        )
        campos += ['ruta_polyline', 'distancia_km', 'tiempo_estimado_min']

    # Un solo save: así la señal del historial ve el estado final completo
    # (incluido el puesto en la ruta, que va en la notificación).
    pedido.save(update_fields=campos)


def intentar_despachar(pedido, config=None):
    """Manda el pedido a la calle si hay repartidor; si no, a la cola.

    Devuelve True solo si quedó EN_CAMINO.
    """
    if pedido.repartidor_id or pedido.estado not in (
        Pedido.Estado.PREPARANDO, Pedido.Estado.PENDIENTE,
    ):
        return False

    config = config or obtener_configuracion_entrega()
    perfil = _elegir_repartidor(pedido, config)

    if not perfil:
        # Ya está preparado pero no hay a quién dárselo: espera en la cola.
        if pedido.estado != Pedido.Estado.PENDIENTE:
            pedido.estado = Pedido.Estado.PENDIENTE
            pedido.save(update_fields=['estado'])
        return False

    _asignar(pedido, perfil, config)
    return True


def procesar_pedidos_listos():
    """Un "tick" del motor: avanza todo lo que ya puede avanzar.

    Lo llaman los endpoints en vivo, así que corre solo mientras alguien
    tenga un panel abierto — que es exactamente cuando importa.
    """
    config = obtener_configuracion_entrega()
    listo_desde = timezone.now() - timedelta(minutes=config.minutos_preparacion)

    # La cola primero: son los que llevan más rato esperando repartidor.
    cola = list(Pedido.objects
                .filter(estado=Pedido.Estado.PENDIENTE, repartidor__isnull=True)
                .order_by('fecha_creacion'))
    recien_listos = list(Pedido.objects
                         .filter(estado=Pedido.Estado.PREPARANDO,
                                 fecha_creacion__lte=listo_desde)
                         .order_by('fecha_creacion'))

    return sum(1 for pedido in cola + recien_listos if intentar_despachar(pedido, config))


def asignar_pendientes_a(perfil_emple):
    """Le carga la cola pendiente a un repartidor que recién arranca.

    Es el caso que pedía el negocio: si se acumularon pedidos preparados
    porque no había nadie repartiendo, el primero que sale se lleva varios
    de una, en orden de llegada (el que más esperó, primera parada).
    """
    if perfil_emple.rol != 'empleado' or not perfil_emple.disponible:
        return 0

    config = obtener_configuracion_entrega()
    activas = Pedido.objects.filter(
        repartidor=perfil_emple.empleado, estado=Pedido.Estado.EN_CAMINO,
    ).count()

    cupo_pedidos = config.max_pedidos_por_repartidor - activas
    if cupo_pedidos <= 0:
        return 0

    cola = (Pedido.objects
            .filter(estado=Pedido.Estado.PENDIENTE, repartidor__isnull=True)
            .order_by('fecha_creacion'))

    carga = carga_actual(perfil_emple.empleado)
    asignados = 0

    for pedido in cola:
        if asignados >= cupo_pedidos:
            break

        # Lo que no le cabe se lo salta y sigue con el siguiente: un
        # pedido grande no puede frenar toda la cola detrás de él.
        unidades = unidades_de(pedido)
        if carga + unidades > perfil_emple.capacidad_productos:
            continue

        _asignar(pedido, perfil_emple, config)
        carga += unidades
        asignados += 1

    return asignados


def recompactar_ruta(empleado):
    """Cierra el hueco en la numeración cuando una entrega se completa.

    Sin esto, al entregar la parada #1 las demás se quedan en #2 y #3 y el
    cliente sigue viendo "hay 1 antes del tuyo" cuando ya no hay ninguna.
    No recalcula tiempos acá: eso lo hace el siguiente ping de GPS del
    repartidor, que es cuando de verdad cambió la distancia.
    """
    activos = (Pedido.objects
               .filter(repartidor=empleado, estado=Pedido.Estado.EN_CAMINO)
               .order_by('orden_en_ruta', 'fecha_creacion'))

    for puesto, pedido in enumerate(activos, start=1):
        if pedido.orden_en_ruta != puesto:
            pedido.orden_en_ruta = puesto
            pedido.save(update_fields=['orden_en_ruta'])
