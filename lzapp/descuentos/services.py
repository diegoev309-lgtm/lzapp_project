import random

from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone
from dashboard.models import CampanaDescuento, DescuentoAsignado, DetalleVenta


def obtener_ids_clientes_elegibles(campana: CampanaDescuento, producto):
    """
    Devuelve solo los IDs (no los objetos completos, para no cargar
    memoria de más) de los clientes que:
    - no son staff/admin
    - NO han comprado ESTE producto en los últimos `dias_sin_compra` días
      (o nunca lo han comprado)
    - no tienen ya un premio de esta campaña para este producto
    """
    limite_fecha = timezone.now() - timedelta(days=campana.dias_sin_compra)

    usuarios_que_si_compraron = DetalleVenta.objects.filter(
        producto=producto,
        venta__fecha__gte=limite_fecha,
    ).values_list('venta__usuario_id', flat=True)

    usuarios_con_premio_previo = DescuentoAsignado.objects.filter(
        campana=campana,
        producto=producto,
    ).values_list('usuario_id', flat=True)

    ids = (
        User.objects.filter(is_staff=False, is_active=True)
        .exclude(id__in=usuarios_que_si_compraron)
        .exclude(id__in=usuarios_con_premio_previo)
        .values_list('id', flat=True)
    )
    return list(ids)


def calcular_stock_disponible_para_oferta(producto):
    """
    Stock que sí se puede comprometer en la oferta, dejando intacto
    tanto el stock_minimo del producto como el colchón extra de la
    campaña (stock_reservado_no_ofertable).
    """
    return max(producto.stock_actual - producto.stock_minimo, 0)


def calcular_limite_clientes(campana: CampanaDescuento, producto):
    """
    Calcula CUÁNTOS clientes realmente pueden recibir el premio para
    este producto, cruzando las 3 restricciones:
      1) tope configurado (cantidad_clientes)
      2) % máximo de la base total de clientes activos
      3) stock disponible (menos el colchón reservado)

    Devuelve un dict con el detalle, para poder informarlo/loguearlo
    ANTES de ejecutar el sorteo (ideal para mostrarlo en el admin o
    en una vista de "previsualizar campaña").
    """
    total_clientes_activos = User.objects.filter(is_staff=False, is_active=True).count()
    limite_por_porcentaje = int(total_clientes_activos * (campana.porcentaje_maximo_clientes / 100))

    stock_bruto_disponible = calcular_stock_disponible_para_oferta(producto)
    stock_ofertable = max(stock_bruto_disponible - campana.stock_reservado_no_ofertable, 0)

    ids_elegibles = obtener_ids_clientes_elegibles(campana, producto)

    limite_final = min(
        campana.cantidad_clientes,
        limite_por_porcentaje,
        stock_ofertable,
        len(ids_elegibles),
    )

    return {
        'producto': producto.nombre,
        'total_clientes_activos': total_clientes_activos,
        'limite_por_porcentaje': limite_por_porcentaje,
        'stock_ofertable': stock_ofertable,
        'clientes_elegibles_encontrados': len(ids_elegibles),
        'clientes_que_recibiran_el_premio': limite_final,
        'ids_elegibles': ids_elegibles,
    }


def previsualizar_campana(campana: CampanaDescuento):
    """
    Muestra, SIN crear ningún registro todavía, a cuántos clientes se
    les aplicaría el descuento por cada producto de la campaña.
    Útil para revisar antes de lanzarla de verdad.
    """
    if not campana.esta_vigente():
        return {'campana': campana.nombre, 'error': 'La campaña no está activa o está fuera de fechas.'}

    detalle = [calcular_limite_clientes(campana, producto) for producto in campana.productos.all()]
    return {'campana': campana.nombre, 'detalle': detalle}


def ejecutar_campana(campana: CampanaDescuento):
    """
    Corre el sorteo de UNA campaña: por cada producto, calcula el
    límite real de clientes (stock + % + tope), sortea sobre los IDs
    elegibles (liviano en memoria) y crea el DescuentoAsignado de cada
    ganador.
    """
    resumen = {'campana': campana.nombre, 'productos': []}

    if not campana.esta_vigente():
        resumen['error'] = 'La campaña no está activa o está fuera de fechas.'
        return resumen

    for producto in campana.productos.all():
        calculo = calcular_limite_clientes(campana, producto)
        limite = calculo['clientes_que_recibiran_el_premio']

        if limite <= 0:
            resumen['productos'].append({**calculo, 'motivo_si_cero': 'sin stock, sin cupo de % o sin elegibles'})
            continue

        ids_ganadores = random.sample(calculo['ids_elegibles'], limite)

        precio_original = producto.precio
        descuento = precio_original * (campana.porcentaje_descuento / 100)
        precio_final = round(precio_original - descuento, 2)

        creados = 0
        for usuario in User.objects.filter(id__in=ids_ganadores).iterator():
            DescuentoAsignado.objects.create(
                campana=campana,
                usuario=usuario,
                producto=producto,
                precio_original=precio_original,
                precio_con_descuento=precio_final,
                fecha_expiracion=timezone.now() + timedelta(days=campana.dias_validez_premio),
            )
            creados += 1

        resumen['productos'].append({
            **calculo,
            'ganadores_creados': creados,
            'precio_final': str(precio_final),
        })

    campana.ultima_ejecucion = timezone.now()
    campana.save(update_fields=['ultima_ejecucion'])
    return resumen


def ejecutar_campanas_pendientes():
    """
    Recorre TODAS las campañas activas y ejecuta las que les toque
    según su frecuencia (semanal/mensual). Esto es lo que se llama
    desde el comando programado (cron / Celery beat).
    """
    resultados = []
    for campana in CampanaDescuento.objects.filter(activo=True):
        if campana.debe_ejecutarse():
            resultados.append(ejecutar_campana(campana))
    return resultados


def obtener_premio_activo_para_home(usuario):
    """
    Para usar directamente en la vista del home: devuelve el premio
    (DescuentoAsignado) más reciente y aún vigente para mostrar la
    tarjeta de "ganaste un descuento", o None si no tiene ninguno.
    """
    return (
        DescuentoAsignado.objects
        .filter(usuario=usuario, usado=False, fecha_expiracion__gte=timezone.now())
        .order_by('-fecha_asignacion')
        .first()
    )