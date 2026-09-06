"""Sugerencias que el sistema le propone al admin mirando el historial.

El admin ya no mueve estados a mano (de eso se encarga asignacion.py),
pero sigue siendo quien decide la configuración del negocio. Este módulo
busca patrones en los pedidos anteriores y, cuando algo se repite, deja
una SugerenciaSistema con el número concreto que recomienda para que el
admin lo aplique o lo descarte de un clic.

Todo sale del historial de estados, que ya se venía guardando:

  * PENDIENTE → EN_CAMINO  = cuánto esperó un pedido ya preparado a que
    hubiera repartidor. Si esa espera es sistemática, la producción va más
    rápido que el reparto y conviene estirar el tiempo de preparación (o
    contratar más gente).
  * EN_CAMINO → ENTREGADO  = cuánto tardó de verdad la entrega. Si siempre
    supera lo estimado, el tiempo por parada está corto y todos los
    clientes ven tiempos que no se cumplen.
"""
from collections import defaultdict
from datetime import timedelta
from statistics import median

from django.utils import timezone

from dashboard.models import (
    HistorialEstadoPedido, Pedido, SugerenciaSistema, obtener_configuracion_entrega,
)

# Ventana de análisis y mínimo de datos para no sacar conclusiones de dos
# pedidos sueltos (un día raro no es un patrón).
DIAS_ANALIZADOS = 7
MINIMO_MUESTRAS = 5

# A partir de cuánto vale la pena molestar al admin.
UMBRAL_ESPERA_COLA_MIN = 10   # esperando repartidor, ya preparado
UMBRAL_FALTAN_REPARTIDORES_MIN = 30
UMBRAL_DESVIO_ENTREGA_MIN = 5   # entrega real vs. estimada

# No volver a proponer algo que el admin acaba de descartar.
HORAS_SILENCIO_TRAS_DESCARTE = 24


def _eventos_por_pedido():
    """{pedido_id: [(estado, fecha), ...]} del historial reciente, en orden."""
    desde = timezone.now() - timedelta(days=DIAS_ANALIZADOS)
    filas = (HistorialEstadoPedido.objects
             .filter(fecha__gte=desde)
             .order_by('pedido_id', 'fecha', 'id')
             .values_list('pedido_id', 'estado', 'fecha'))

    eventos = defaultdict(list)
    for pedido_id, estado, fecha in filas:
        eventos[pedido_id].append((estado, fecha))
    return eventos


def _minutos_entre(eventos, desde_estado, hasta_estado):
    """Minutos entre la primera vez que entró a un estado y la primera vez
    que entró al siguiente. None si ese tramo no se completó."""
    inicio = None
    for estado, fecha in eventos:
        if estado == desde_estado and inicio is None:
            inicio = fecha
        elif estado == hasta_estado and inicio is not None:
            return (fecha - inicio).total_seconds() / 60
    return None


def _guardar(tipo, mensaje, valor_actual, valor_sugerido, muestras):
    """Deja (o actualiza) la sugerencia pendiente de ese tipo.

    Una sola viva por tipo: si el patrón sigue ahí, se refresca con los
    números nuevos en vez de acumular avisos repetidos.
    """
    reciente = timezone.now() - timedelta(hours=HORAS_SILENCIO_TRAS_DESCARTE)
    descartada_hace_poco = SugerenciaSistema.objects.filter(
        tipo=tipo,
        estado=SugerenciaSistema.Estado.DESCARTADA,
        fecha_actualizacion__gte=reciente,
    ).exists()
    if descartada_hace_poco:
        return None

    sugerencia, _creada = SugerenciaSistema.objects.update_or_create(
        tipo=tipo,
        estado=SugerenciaSistema.Estado.PENDIENTE,
        defaults={
            'mensaje': mensaje[:255],
            'valor_actual': valor_actual,
            'valor_sugerido': valor_sugerido,
            'muestras': muestras,
        },
    )
    return sugerencia


def _cerrar_pendiente(tipo):
    """El patrón ya no está: se retira la sugerencia sin marcarla aplicada."""
    SugerenciaSistema.objects.filter(
        tipo=tipo, estado=SugerenciaSistema.Estado.PENDIENTE,
    ).delete()


def _analizar_espera_en_cola(eventos, config):
    esperas = [
        m for m in (
            _minutos_entre(evs, Pedido.Estado.PENDIENTE, Pedido.Estado.EN_CAMINO)
            for evs in eventos.values()
        ) if m is not None
    ]

    if len(esperas) < MINIMO_MUESTRAS:
        return

    espera_tipica = median(esperas)

    if espera_tipica >= UMBRAL_FALTAN_REPARTIDORES_MIN:
        _guardar(
            SugerenciaSistema.Tipo.FALTAN_REPARTIDORES,
            f'Los pedidos llevan una espera típica de {espera_tipica:.0f} min ya '
            f'preparados porque no hay repartidor libre. Con {len(esperas)} pedidos '
            f'así, el cuello de botella es el reparto, no la cocina.',
            valor_actual=config.max_pedidos_por_repartidor,
            valor_sugerido=None,
            muestras=len(esperas),
        )
        _cerrar_pendiente(SugerenciaSistema.Tipo.TIEMPO_PREPARACION)
        return

    if espera_tipica >= UMBRAL_ESPERA_COLA_MIN:
        sugerido = min(config.minutos_preparacion + int(round(espera_tipica)), 600)
        _guardar(
            SugerenciaSistema.Tipo.TIEMPO_PREPARACION,
            f'Los últimos {len(esperas)} pedidos esperaron unos {espera_tipica:.0f} min '
            f'ya preparados, sin repartidor libre. Subir la preparación a {sugerido} min '
            f'acompasa la cocina con el reparto y le da al cliente un tiempo real.',
            valor_actual=config.minutos_preparacion,
            valor_sugerido=sugerido,
            muestras=len(esperas),
        )
        return

    _cerrar_pendiente(SugerenciaSistema.Tipo.TIEMPO_PREPARACION)
    _cerrar_pendiente(SugerenciaSistema.Tipo.FALTAN_REPARTIDORES)


def _analizar_desvio_entregas(eventos, config):
    """Compara lo que tardó de verdad la entrega contra lo que se prometió."""
    estimados = dict(
        Pedido.objects
        .filter(id__in=eventos.keys(), tiempo_estimado_min__isnull=False)
        .values_list('id', 'tiempo_estimado_min')
    )

    desvios = []
    for pedido_id, evs in eventos.items():
        estimado = estimados.get(pedido_id)
        if not estimado:
            continue
        real = _minutos_entre(evs, Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO)
        if real is not None:
            desvios.append(real - estimado)

    if len(desvios) < MINIMO_MUESTRAS:
        return

    desvio_tipico = median(desvios)
    if desvio_tipico < UMBRAL_DESVIO_ENTREGA_MIN:
        _cerrar_pendiente(SugerenciaSistema.Tipo.MINUTOS_PARADA)
        return

    sugerido = min(config.minutos_por_parada + int(round(desvio_tipico)), 120)
    _guardar(
        SugerenciaSistema.Tipo.MINUTOS_PARADA,
        f'Las entregas están tardando unos {desvio_tipico:.0f} min más de lo estimado '
        f'({len(desvios)} pedidos). Subir el tiempo por parada a {sugerido} min hace '
        f'que los tiempos que ve el cliente se cumplan.',
        valor_actual=config.minutos_por_parada,
        valor_sugerido=sugerido,
        muestras=len(desvios),
    )


def generar_sugerencias():
    """Revisa el historial reciente y actualiza las sugerencias vivas."""
    eventos = _eventos_por_pedido()
    if not eventos:
        return SugerenciaSistema.objects.none()

    config = obtener_configuracion_entrega()
    _analizar_espera_en_cola(eventos, config)
    _analizar_desvio_entregas(eventos, config)

    return sugerencias_pendientes()


def sugerencias_pendientes():
    return SugerenciaSistema.objects.filter(estado=SugerenciaSistema.Estado.PENDIENTE)


def aplicar_sugerencia(sugerencia):
    """Guarda el valor recomendado en la configuración del negocio."""
    config = obtener_configuracion_entrega()

    if sugerencia.valor_sugerido:
        if sugerencia.tipo == SugerenciaSistema.Tipo.TIEMPO_PREPARACION:
            config.minutos_preparacion = sugerencia.valor_sugerido
            config.save(update_fields=['minutos_preparacion'])
        elif sugerencia.tipo == SugerenciaSistema.Tipo.MINUTOS_PARADA:
            config.minutos_por_parada = sugerencia.valor_sugerido
            config.save(update_fields=['minutos_por_parada'])

    sugerencia.estado = SugerenciaSistema.Estado.APLICADA
    sugerencia.save(update_fields=['estado'])
    return config
