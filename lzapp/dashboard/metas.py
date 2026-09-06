"""Metas del negocio propuestas por el sistema.

La idea es que nadie tenga que inventar el número. El motor mira lo que
de verdad pasó en los períodos anteriores, saca un promedio y propone una
meta con un margen de crecimiento. El admin la acepta, la ajusta o la
descarta — pero parte de un dato, no de una corazonada.

Dos decisiones que valen la pena explicar:

  * Se exige un mínimo de períodos con actividad antes de proponer nada.
    Con un solo mes de historia, "el promedio" es ese mes, y proponer un
    +10% sobre un dato suelto es inventar con pasos extra.

  * El período en curso NO entra en el promedio. Si hoy es día 3 del mes,
    ese mes lleva tres días de ventas: meterlo hundiría el promedio y la
    meta saldría ridículamente baja.
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.models import User
from django.db.models import Count, Sum
from django.utils import timezone

from dashboard.models import DetalleVenta, Meta, Pedido, Produccion, Venta

# Cuánto se le pide crecer respecto al promedio histórico.
MARGEN_CRECIMIENTO = Decimal('1.10')

# Períodos cerrados que se miran hacia atrás, y mínimo con actividad
# para que el promedio signifique algo.
PERIODOS_ANALIZADOS = 3
MINIMO_PERIODOS_CON_DATOS = 2


def _rango_mes(referencia):
    """Primer y último día del mes al que pertenece `referencia`."""
    inicio = referencia.replace(day=1)
    siguiente = (inicio + timedelta(days=32)).replace(day=1)
    return inicio, siguiente - timedelta(days=1)


def _rango_semana(referencia):
    """Lunes a domingo de la semana de `referencia`."""
    inicio = referencia - timedelta(days=referencia.weekday())
    return inicio, inicio + timedelta(days=6)


def periodo_actual(tipo_periodo, hoy=None):
    hoy = hoy or timezone.localdate()
    return _rango_semana(hoy) if tipo_periodo == Meta.Periodo.SEMANAL else _rango_mes(hoy)


def _periodos_anteriores(tipo_periodo, cantidad, hoy=None):
    """Los últimos `cantidad` períodos YA CERRADOS, del más viejo al más nuevo."""
    hoy = hoy or timezone.localdate()
    rangos = []
    cursor = periodo_actual(tipo_periodo, hoy)[0]

    for _ in range(cantidad):
        cursor = cursor - timedelta(days=1)          # cae en el período anterior
        inicio, fin = (_rango_semana(cursor) if tipo_periodo == Meta.Periodo.SEMANAL
                       else _rango_mes(cursor))
        rangos.append((inicio, fin))
        cursor = inicio

    return list(reversed(rangos))


# ---------------------------------------------------------------
# Cuánto se logró de cada cosa en un rango de fechas
# ---------------------------------------------------------------
def _ventas_en(inicio, fin):
    total = (Venta.objects
             .filter(fecha__date__gte=inicio, fecha__date__lte=fin)
             .exclude(pedido__estado=Pedido.Estado.CANCELADO)
             .aggregate(t=Sum('total'))['t'])
    return Decimal(total or 0)


def _produccion_en(inicio, fin):
    total = (Produccion.objects
             .filter(fecha_produccion__date__gte=inicio, fecha_produccion__date__lte=fin)
             .aggregate(t=Sum('cantidad_producida'))['t'])
    return Decimal(total or 0)


def _clientes_en(inicio, fin):
    # Solo clientes: los empleados y admins no son crecimiento comercial.
    total = (User.objects
             .filter(date_joined__date__gte=inicio, date_joined__date__lte=fin,
                     is_staff=False, is_superuser=False)
             .exclude(perfilemple__rol='empleado')
             .count())
    return Decimal(total)


def _pedidos_en(inicio, fin):
    total = (Pedido.objects
             .filter(fecha_creacion__date__gte=inicio, fecha_creacion__date__lte=fin,
                     estado=Pedido.Estado.ENTREGADO)
             .count())
    return Decimal(total)


MEDIDORES = {
    Meta.Tipo.VENTAS:     (_ventas_en,     Meta.Periodo.MENSUAL),
    Meta.Tipo.PRODUCCION: (_produccion_en, Meta.Periodo.SEMANAL),
    Meta.Tipo.CLIENTES:   (_clientes_en,   Meta.Periodo.MENSUAL),
    Meta.Tipo.PEDIDOS:    (_pedidos_en,    Meta.Periodo.MENSUAL),
}


def logro_actual(meta):
    """Cuánto se lleva logrado de esta meta en su propio período."""
    medidor, _ = MEDIDORES[meta.tipo]
    return medidor(meta.fecha_inicio, meta.fecha_fin)


def progreso(meta):
    """Porcentaje logrado, tope 100 para no romper el anillo del panel."""
    if not meta.objetivo:
        return 0
    pct = (logro_actual(meta) / meta.objetivo) * 100
    return int(min(pct, Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _redondear(valor, tipo):
    """Un objetivo tiene que ser legible: nadie se pone la meta de vender
    $247.813,44. Los montos se redondean a miles y las unidades a enteros."""
    if tipo == Meta.Tipo.VENTAS:
        miles = (valor / 1000).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        return max(miles, Decimal('1')) * 1000
    return max(valor.quantize(Decimal('1'), rounding=ROUND_HALF_UP), Decimal('1'))


def calcular_propuesta(tipo, hoy=None):
    """Meta sugerida para el período en curso, o None si no hay historia.

    Devuelve (objetivo, promedio_historico, periodos_con_datos).
    """
    medidor, tipo_periodo = MEDIDORES[tipo]
    rangos = _periodos_anteriores(tipo_periodo, PERIODOS_ANALIZADOS, hoy)

    valores = [medidor(inicio, fin) for inicio, fin in rangos]
    con_datos = [v for v in valores if v > 0]

    if len(con_datos) < MINIMO_PERIODOS_CON_DATOS:
        return None

    promedio = sum(con_datos) / len(con_datos)
    objetivo = _redondear(promedio * MARGEN_CRECIMIENTO, tipo)
    return objetivo, promedio, len(con_datos)


def generar_propuestas(hoy=None):
    """Crea las metas propuestas que falten para el período en curso.

    No pisa una meta que el admin ya aceptó ni vuelve a proponer una que
    descartó para este mismo período: se respeta lo que ya decidió.
    """
    hoy = hoy or timezone.localdate()
    creadas = []

    for tipo, (_, tipo_periodo) in MEDIDORES.items():
        inicio, fin = periodo_actual(tipo_periodo, hoy)

        ya_existe = Meta.objects.filter(
            tipo=tipo, fecha_inicio=inicio, fecha_fin=fin,
        ).exists()
        if ya_existe:
            continue

        calculo = calcular_propuesta(tipo, hoy)
        if not calculo:
            continue

        objetivo, promedio, periodos = calculo
        creadas.append(Meta.objects.create(
            tipo=tipo,
            periodo=tipo_periodo,
            estado=Meta.Estado.PROPUESTA,
            objetivo=objetivo,
            fecha_inicio=inicio,
            fecha_fin=fin,
            base_historica=promedio.quantize(Decimal('0.01')),
            periodos_analizados=periodos,
        ))

    return creadas


def marcar_cumplidas():
    """Pasa a 'cumplida' las metas activas que ya llegaron a su objetivo."""
    cumplidas = 0
    for meta in Meta.objects.filter(estado=Meta.Estado.ACTIVA):
        if logro_actual(meta) >= meta.objetivo:
            meta.estado = Meta.Estado.CUMPLIDA
            meta.save(update_fields=['estado'])
            cumplidas += 1
    return cumplidas


def con_progreso(metas):
    """Adorna cada meta con su avance, para no recalcularlo en la plantilla."""
    resultado = []
    for meta in metas:
        logro = logro_actual(meta)
        resultado.append({
            'meta': meta,
            'logro': logro,
            'progreso': progreso(meta),
            'restante': max(meta.objetivo - logro, Decimal('0')),
        })
    return resultado
