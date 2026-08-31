from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q, Avg, Count, OuterRef, Subquery, Value, IntegerField
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from dashboard.models import Producto, Calificacion,TiradaDiaria
from carrito.logic import limpiar_premios_invalidos_del_carrito, premio_ya_en_carrito
from descuentos.services import obtener_premio_activo_para_home, obtener_producto_ids_con_premio_activo



def obtener_productos_filtrados(request, excluir_ids=None):
    query = request.GET.get('q', '').strip()

    mi_calificacion_sub = None
    if request.user.is_authenticated:
        mi_calificacion_sub = Calificacion.objects.filter(
            producto=OuterRef('pk'), usuario=request.user
        ).values('puntaje')[:1]

    productos = Producto.objects.filter(disponibilidad=True).annotate(
        promedio_calificacion=Avg('calificaciones__puntaje'),
        total_calificaciones=Count('calificaciones', distinct=True),
        mi_calificacion=Subquery(mi_calificacion_sub) if mi_calificacion_sub is not None else Value(None, output_field=IntegerField()),
    )

    if excluir_ids:
        productos = productos.exclude(id__in=excluir_ids)

    if query:
        productos = productos.filter(Q(nombre__icontains=query) | Q(descripcion__icontains=query))

    return productos, query


def buscar_productos_ajax(request):

    #Endpoint JSON puro: lo consume el fetch() del buscador en vivo del
    #template. Antes esta función hacía DOS cosas a la vez (filtrar Y
    #devolver JSON), y por eso main()/carro() se rompían al intentar
    #desempaquetarla como si devolviera (productos, query): un JsonResponse
    #no es una tupla.

    productos, query = obtener_productos_filtrados(request)

    resultados = []
    for p in productos:
        resultados.append({
            "id": p.id,
            "nombre": p.nombre,
            "descripcion": p.descripcion or "",
            "precio": str(p.precio),
            "stock_actual": p.stock_actual,
            "stock_minimo": p.stock_minimo,
            "imagen": p.imagen.url if p.imagen else static('img/no-image.png'),
            "promedio_calificacion": round(p.promedio_calificacion, 1) if p.promedio_calificacion else None,
            "total_calificaciones": p.total_calificaciones,
            "mi_calificacion": p.mi_calificacion,
        })

    return JsonResponse({"productos": resultados, "query": query})


def _premio_activo_o_none(request, solo_mostrados=False):
    """Evita repetir el chequeo is_authenticated en cada vista del home."""
    if request.user.is_authenticated:
        return obtener_premio_activo_para_home(request.user, solo_mostrados=solo_mostrados)
    return None


def _premio_para_animacion(request):
    """
    Para el home: si el usuario ya reclamó el premio (está en su carrito),
    no vuelve a mostrar la animación/tarjeta de "ganaste" — ya la vio y
    ya actuó. Solo se muestra mientras siga sin reclamar.
    """
    premio = _premio_activo_o_none(request)
    if premio and premio_ya_en_carrito(request, premio.codigo):
        return None
    return premio


def _estado_juego_diario(request):
    """
    Estado de la ruleta diaria, para llenar el "hueco vacío" de
    oferta-globo-wrap cuando el usuario NO tiene premio_activo de campaña
    oficial (sin campaña vigente, no sorteado, o visitante anónimo).
    Todos pueden jugar una vez al día, registrados y anónimos.

    Devuelve un dict con 'estado' en:
      - 'disponible': todavía no jugó hoy -> puede tocar los quesos y sortear.
      - 'ganado': jugó y ganó (CUPON_5/ENVIO_GRATIS/BOLETO_DORADO) -> incluye
        la tirada, para mostrar la tarjeta de resultado + botón reclamar.
      - 'sin_premio': jugó y salió SIGUE_INTENTANDO -> "vuelve mañana".
    """
    hoy = timezone.now().date()
    if request.user.is_authenticated:
        tirada = TiradaDiaria.objects.filter(usuario=request.user, fecha=hoy).first()
    else:
        session_key = request.session.session_key
        tirada = (
            TiradaDiaria.objects.filter(sesion_key=session_key, fecha=hoy, usuario__isnull=True).first()
            if session_key else None
        )

    if not tirada:
        return {'estado': 'disponible'}
    if tirada.resultado == TiradaDiaria.Resultado.SIGUE_INTENTANDO:
        return {'estado': 'sin_premio', 'tirada': tirada}
    return {'estado': 'ganado', 'tirada': tirada}


def main(request):
    premio_para_animacion = _premio_para_animacion(request)
    # Prioridad: si hay premio de campaña oficial, se muestra tal cual
    # (sin cambios). Si no, se llena el hueco con el estado de la ruleta
    # diaria en vez de dejar oferta-globo-wrap oculto.
    juego_diario = None if premio_para_animacion else _estado_juego_diario(request)
    ids_con_premio = obtener_producto_ids_con_premio_activo(request.user) if request.user.is_authenticated else set()
    productos, query = obtener_productos_filtrados(request, excluir_ids=ids_con_premio)
    context = {
        'productos': productos,
        'query': query,
        'premio_activo': premio_para_animacion,
        'juego_diario': juego_diario,
    }
    return render(request, "masterpage.html", context)
    #return render(request, "masterpage1.html", context)


def user(request):
    productos = Producto.objects.filter(disponibilidad=True)
    return render(request, "users.html", {"productos": productos})
    #return render(request, "usuarios/usuarios.html", {"productos": productos})


def client(request):
    premio_activo = _premio_activo_o_none(request)
    juego_diario = None if premio_activo else _estado_juego_diario(request)
    ids_con_premio = obtener_producto_ids_con_premio_activo(request.user) if request.user.is_authenticated else set()
    productos, query = obtener_productos_filtrados(request, excluir_ids=ids_con_premio)
    context = {
        'productos': productos,
        'query': query,
        'premio_activo': premio_activo,
        'juego_diario': juego_diario,
    }
    return render(request, "clients.html", context)
    #return render(request, "usuarios/clientes.html", context)

@ensure_csrf_cookie
def carro(request):
    limpiar_premios_invalidos_del_carrito(request)
    ids_con_premio = obtener_producto_ids_con_premio_activo(request.user) if request.user.is_authenticated else set()
    productos, query = obtener_productos_filtrados(request, excluir_ids=ids_con_premio)
    pago_status = None
    payment_id = request.GET.get("payment_id")
    status_mp = request.GET.get("status") or request.GET.get("collection_status")

    if status_mp:
        if status_mp == "approved":
            pago_status = "exitoso"
            comprados = request.session.pop("mp_items_comprados", [])
            carro = request.session.get("carro", {})
            for pid in comprados:
                carro.pop(pid, None)
            request.session["carro"] = carro
            request.session.modified = True
        elif status_mp in ("pending", "in_process"):
            pago_status = "pendiente"
        else:
            pago_status = "fallido"
            request.session.pop("mp_items_comprados", None)

    premio_activo = _premio_activo_o_none(request, solo_mostrados=True)
    juego_diario = None if premio_activo else _estado_juego_diario(request)

    from dashboard.models import Perfil
    
    perfil_cliente = None
    if request.user.is_authenticated:
        perfil_cliente = Perfil.objects.filter(usuario=request.user).first()

    context = {
        "productos": productos,
        "query": query,
        'premio_activo': premio_activo,
        'juego_diario': juego_diario,
        "pago_status": pago_status,
        "pago_payment_id": payment_id,
        "perfil_latitud": perfil_cliente.latitud if perfil_cliente else None,
        "perfil_longitud": perfil_cliente.longitud if perfil_cliente else None,
    }
    return render(request, "carrito_compras.html", context)
    #return render(request, "carrito/carrito_compras.html", context)