import random

from datetime import timedelta
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.utils import timezone
from dashboard.models import CampanaDescuento, DescuentoAsignado, DetalleVenta, Producto
from .models import TiradaDiaria


# =========================================================
# 0) SUGERENCIA DE VENCIMIENTO (solo visual, para el modal
#    de creación/edición de campaña — no autoselecciona nada)
# =========================================================

def calcular_badge_vencimiento(fecha_vencimiento):
    #"""
    #Traduce una fecha_vencimiento en el badge que se debe mostrar junto
    #al checkbox del producto en formdes.html. Devuelve None si no hay
    #fecha cargada o si falta demasiado tiempo para preocuparse.
    #"""
    if not fecha_vencimiento:
        return None

    dias = (fecha_vencimiento - timezone.now().date()).days

    if dias < 0:
        return {'clase': 'rojo', 'texto': f'⚠️ Vencido hace {abs(dias)} días'}
    if dias <= 7:
        return {'clase': 'rojo', 'texto': f'⚠️ Vence en {dias} días'}
    if dias <= 30:
        return {'clase': 'amarillo', 'texto': f'Vence en {dias} días'}
    return None


def obtener_badges_vencimiento_productos():
    #"""
    #dict {str(producto_id): {'clase': ..., 'texto': ...}} con solo los
    #productos que sí ameritan badge. Se usa en crear/editar campaña para
    #resaltar los checkboxes de productos próximos a vencer.
    #"""
    badges = {}
    for p in Producto.objects.all().only('id', 'fecha_vencimiento'):
        badge = calcular_badge_vencimiento(p.fecha_vencimiento)
        if badge:
            badges[str(p.id)] = badge
    return badges


def obtener_ids_usuarios_con_boleto_dorado_vigente():
    #"""
    #IDs de usuarios con un "boleto dorado" (TiradaDiaria de la ruleta
    #diaria) reclamado, aún no consumido en ninguna ejecución de campaña,
    #y todavía dentro de sus 7 días de vigencia. Se usa tanto para armar
    #el pool de elegibles como para marcar boleto_usado tras ejecutar.
    #"""
    return set(
        TiradaDiaria.objects.filter(
            resultado=TiradaDiaria.Resultado.BOLETO_DORADO,
            reclamado=True,
            boleto_usado=False,
            fecha_expiracion__gte=timezone.now(),
            usuario__isnull=False,
            usuario__is_staff=False,
            usuario__is_active=True,
        ).values_list('usuario_id', flat=True)
    )


def obtener_ids_clientes_elegibles(campana: CampanaDescuento, producto):
    #"""
    #Devuelve solo los IDs (no los objetos completos, para no cargar
    #memoria de más) de los clientes que:
    #- no son staff/admin
    #- NO han comprado ESTE producto en los últimos `dias_sin_compra` días
    #  (o nunca lo han comprado)
    #- no tienen ya un premio de esta campaña para este producto
    #
    #Excepción: los usuarios con un "boleto dorado" vigente (ganado en la
    #ruleta diaria) entran igual al pool AUNQUE sí hayan comprado el
    #producto recientemente — el boleto solo los mete a competir, no les
    #garantiza nada; el tope final (cantidad_clientes/%/stock) y el sorteo
    #siguen aplicando igual. Eso sí, se respeta la exclusión de "ya tiene
    #premio de esta campaña para este producto", porque de lo contrario
    #chocaría con la restricción única de DescuentoAsignado al crearlo.
    #"""
    limite_fecha = timezone.now() - timedelta(days=campana.dias_sin_compra)

    usuarios_que_si_compraron = DetalleVenta.objects.filter(
        producto=producto,
        venta__fecha__gte=limite_fecha,
    ).values_list('venta__usuario_id', flat=True)

    usuarios_con_premio_previo = set(
        DescuentoAsignado.objects.filter(
            campana=campana,
            producto=producto,
        ).values_list('usuario_id', flat=True)
    )

    ids_normales = set(
        User.objects.filter(is_staff=False, is_active=True)
        .exclude(id__in=usuarios_que_si_compraron)
        .exclude(id__in=usuarios_con_premio_previo)
        .values_list('id', flat=True)
    )

    ids_boleto_dorado = obtener_ids_usuarios_con_boleto_dorado_vigente() - usuarios_con_premio_previo

    return list(ids_normales | ids_boleto_dorado)


def calcular_stock_disponible_para_oferta(producto):
    #"""
    #Stock que sí se puede comprometer en la oferta, dejando intacto
    #tanto el stock_minimo del producto como el colchón extra de la
    #campaña (stock_reservado_no_ofertable).
    #"""
    return max(producto.stock_actual - producto.stock_minimo, 0)


def calcular_limite_clientes(campana: CampanaDescuento, producto):
    #"""
    #Calcula CUÁNTOS clientes realmente pueden recibir el premio para
    #este producto, cruzando las 3 restricciones:
    #  1) tope configurado (cantidad_clientes)
    #  2) % máximo de la base total de clientes activos
    #  3) stock disponible (menos el colchón reservado)
#
    #Devuelve un dict con el detalle, para poder informarlo/loguearlo
    #ANTES de ejecutar el sorteo (ideal para mostrarlo en el admin o
    #en una vista de "previsualizar campaña").
    #"""
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
    #"""
    #Muestra, SIN crear ningún registro todavía, a cuántos clientes se
    #les aplicaría el descuento por cada producto de la campaña.
    #Útil para revisar antes de lanzarla de verdad.
    #"""
    if not campana.esta_vigente():
        return {'campana': campana.nombre, 'error': 'La campaña no está activa o está fuera de fechas.'}

    detalle = [calcular_limite_clientes(campana, producto) for producto in campana.productos.all()]
    return {'campana': campana.nombre, 'detalle': detalle}


def ejecutar_campana(campana: CampanaDescuento):
    #"""
    #Corre el sorteo de UNA campaña: por cada producto, calcula el
    #límite real de clientes (stock + % + tope), sortea sobre los IDs
    #elegibles (liviano en memoria) y crea el DescuentoAsignado de cada
    #ganador.
    #"""
    resumen = {'campana': campana.nombre, 'productos': []}

    if not campana.esta_vigente():
        resumen['error'] = 'La campaña no está activa o está fuera de fechas.'
        return resumen

    # Se calcula UNA sola vez por ejecución: quiénes tienen boleto dorado
    # vigente en este momento (antes de tocar nada), para poder detectar
    # abajo a cuáles de ellos les tocó entrar al pool de algún producto.
    ids_con_boleto_dorado = obtener_ids_usuarios_con_boleto_dorado_vigente()
    ids_boleto_dorado_usados_en_ejecucion = set()

    for producto in campana.productos.all():
        calculo = calcular_limite_clientes(campana, producto)
        limite = calculo['clientes_que_recibiran_el_premio']

        # El boleto se "consume" con solo entrar al pool de elegibles de
        # este producto, haya ganado o no en el random.sample de abajo.
        ids_boleto_dorado_usados_en_ejecucion |= (
            set(calculo['ids_elegibles']) & ids_con_boleto_dorado
        )

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

    if ids_boleto_dorado_usados_en_ejecucion:
        TiradaDiaria.objects.filter(
            usuario_id__in=ids_boleto_dorado_usados_en_ejecucion,
            resultado=TiradaDiaria.Resultado.BOLETO_DORADO,
            reclamado=True,
            boleto_usado=False,
        ).update(boleto_usado=True)

    campana.ultima_ejecucion = timezone.now()
    campana.save(update_fields=['ultima_ejecucion'])
    return resumen


def ejecutar_campanas_pendientes():
    #"""
    #Recorre TODAS las campañas activas y ejecuta las que les toque
    #según su frecuencia (semanal/mensual). Esto es lo que se llama
    #desde el comando programado (cron / Celery beat).
    #"""
    resultados = []
    for campana in CampanaDescuento.objects.filter(activo=True):
        if campana.debe_ejecutarse():
            resultados.append(ejecutar_campana(campana))
    return resultados


def obtener_premio_activo_para_home(usuario, solo_mostrados=False):
    #"""
    #Para usar directamente en la vista del home: devuelve el premio
    #(DescuentoAsignado) más reciente y aún vigente para mostrar la
    #tarjeta de "ganaste un descuento", o None si no tiene ninguno.
#
    #solo_mostrados=True → solo devuelve el premio si el cliente YA vio
    #la animación de revelación (mostrado=True). Úsalo en cualquier
    #vista que NO sea el home, para que el premio no aparezca "de la
    #nada" antes de que el usuario lo haya reclamado visualmente.
    #"""
    qs = DescuentoAsignado.objects.filter(
        usuario=usuario, usado=False, fecha_expiracion__gte=timezone.now()
    )
    if solo_mostrados:
        qs = qs.filter(mostrado=True)
    return qs.order_by('-fecha_asignacion').first()

def obtener_producto_ids_con_premio_activo(usuario):
    #"""
    #IDs de productos que el usuario tiene con un premio vigente y sin usar
    #(independiente de si ya vio la animación o ya lo agregó al carrito).
    #Se usa para OCULTAR esos productos de la lista normal de catálogo,
    #ya que mientras el descuento siga activo no deben competir con su
    #versión de precio completo.
    #"""
    if not usuario.is_authenticated:
        return set()
    return set(
        DescuentoAsignado.objects
        .filter(usuario=usuario, usado=False, fecha_expiracion__gte=timezone.now())
        .values_list('producto_id', flat=True)
    )


# =========================================================
# 4) JUEGO DIARIO ("Ruleta del día") — PARTE 2
# =========================================================

# Tabla FIJA de premios: hardcodeada a propósito (no es configurable
# desde el dashboard, a diferencia de CampanaDescuento). (código, peso%).
TABLA_PREMIOS_RULETA_DIARIA = [
    (TiradaDiaria.Resultado.SIGUE_INTENTANDO, 65),
    (TiradaDiaria.Resultado.CUPON_5, 15),
    (TiradaDiaria.Resultado.ENVIO_GRATIS, 12),
    (TiradaDiaria.Resultado.BOLETO_DORADO, 8),
]

DIAS_VALIDEZ_PREMIO_RULETA = 7  # misma vigencia que dias_validez_premio por defecto en DescuentoAsignado


def _asegurar_session_key(request):
    #"""
    #Los visitantes anónimos necesitan una session_key real (no None) para
    #poder guardar su TiradaDiaria. Django crea la sesión de forma "perezosa"
    #(solo al primer .save() o al guardar algo en request.session), así que
    #si todavía no existe, la forzamos aquí.
    #"""
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _tirada_de_hoy(request):
    #"""
    #Busca (sin crear) la TiradaDiaria de hoy para el usuario logueado, o
    #para la sesión actual si es anónimo. None si todavía no ha jugado.
    #"""
    hoy = timezone.now().date()
    if request.user.is_authenticated:
        return TiradaDiaria.objects.filter(usuario=request.user, fecha=hoy).first()

    session_key = request.session.session_key
    if not session_key:
        return None
    return TiradaDiaria.objects.filter(
        sesion_key=session_key, fecha=hoy, usuario__isnull=True
    ).first()


def jugar_ruleta_del_dia(request):
    #"""
    #Un solo intento por usuario/sesión por día. Si ya existe tirada de
    #hoy, la devuelve tal cual (NO vuelve a sortear). Si no existe, sortea
    #con random.choices según TABLA_PREMIOS_RULETA_DIARIA y la crea.
    #
    #Devuelve (tirada, es_nueva): es_nueva=False si ya la había jugado hoy.
    #"""
    tirada_existente = _tirada_de_hoy(request)
    if tirada_existente:
        return tirada_existente, False

    codigos = [codigo for codigo, _peso in TABLA_PREMIOS_RULETA_DIARIA]
    pesos = [peso for _codigo, peso in TABLA_PREMIOS_RULETA_DIARIA]
    resultado = random.choices(codigos, weights=pesos, k=1)[0]

    datos = {
        'resultado': resultado,
        'fecha_expiracion': timezone.now() + timedelta(days=DIAS_VALIDEZ_PREMIO_RULETA),
    }
    if request.user.is_authenticated:
        datos['usuario'] = request.user
    else:
        datos['sesion_key'] = _asegurar_session_key(request)

    try:
        tirada = TiradaDiaria.objects.create(**datos)
    except IntegrityError:
        # Condición de carrera: otra petición (doble clic, doble tab) ya
        # creó la tirada de hoy justo antes que esta. No hay que sortear
        # de nuevo, solo devolver la que ya quedó guardada.
        tirada = _tirada_de_hoy(request)

    return tirada, True


def reclamar_premio_dia(request):
    #"""
    #Marca reclamado=True en la tirada de hoy y aplica su efecto:
    #- CUPON_5 / ENVIO_GRATIS -> banderas ligeras en sesión (las consume
    #  carrito.context_processor.totalizar_carro). NO usa DescuentoAsignado
    #  ni toca stock_actual de ningún producto.
    #- BOLETO_DORADO -> solo se marca reclamado=True aquí; el efecto real
    #  ocurre después, dentro de obtener_ids_clientes_elegibles/ejecutar_campana.
    #- SIGUE_INTENTANDO -> no hay nada que reclamar.
    #
    #Devuelve (tirada, estado), con estado en:
    #'ok' | 'sin_premio' | 'ya_reclamado' | 'expirado' | 'no_hay_tirada_hoy'
    #"""
    tirada = _tirada_de_hoy(request)
    if not tirada:
        return None, 'no_hay_tirada_hoy'

    if tirada.resultado == TiradaDiaria.Resultado.SIGUE_INTENTANDO:
        return tirada, 'sin_premio'

    if tirada.reclamado:
        return tirada, 'ya_reclamado'

    if not tirada.esta_vigente():
        return tirada, 'expirado'

    if tirada.resultado == TiradaDiaria.Resultado.CUPON_5:
        request.session['cupon_ruleta'] = {
            'tirada_id': tirada.pk,
            'porcentaje': 5,
            'fecha_expiracion': tirada.fecha_expiracion.isoformat(),
        }
        request.session.modified = True
    elif tirada.resultado == TiradaDiaria.Resultado.ENVIO_GRATIS:
        request.session['envio_gratis_ruleta'] = {
            'tirada_id': tirada.pk,
            'fecha_expiracion': tirada.fecha_expiracion.isoformat(),
        }
        request.session.modified = True
    # BOLETO_DORADO: nada que guardar en sesión, el efecto vive en la BD
    # (se lee vía obtener_ids_usuarios_con_boleto_dorado_vigente).

    tirada.reclamado = True
    tirada.save(update_fields=['reclamado'])
    return tirada, 'ok'