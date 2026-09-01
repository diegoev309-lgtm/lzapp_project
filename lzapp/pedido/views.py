from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from dashboard.models import Pedido, PerfilEmple, Notificacion
from pedido.services import obtener_distancia_km
from seguridad.decorators import vista_dashboard

import requests

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
    """El repartidor reporta su posición actual. Solo se acepta si tiene
    al menos un pedido activo asignado — sin eso, no hay nada que rastrear."""
    perfil_emple = PerfilEmple.objects.filter(empleado=request.user, rol='empleado').first()
    if not perfil_emple:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    tiene_entrega_activa = Pedido.objects.filter(
        repartidor=request.user,
        estado__in=['preparando', 'en_camino'],
    ).exists()

    if not tiene_entrega_activa:
        return JsonResponse({'error': 'No tienes entregas activas asignadas'}, status=403)

    lat = request.POST.get('latitud')
    lng = request.POST.get('longitud')
    if not lat or not lng:
        return JsonResponse({'error': 'Faltan coordenadas'}, status=400)

    perfil_emple.repartidor_latitud = lat
    perfil_emple.repartidor_longitud = lng
    perfil_emple.ubicacion_actualizada = timezone.now()
    perfil_emple.save(update_fields=['repartidor_latitud', 'repartidor_longitud', 'ubicacion_actualizada'])

    pedidos_en_camino = Pedido.objects.filter(
        repartidor=request.user,
        estado='en_camino',
        cliente_latitud__isnull=False,
        notificado_proximidad=False,
    )
    for pedido in pedidos_en_camino:
        distancia_km, _ = obtener_distancia_km(
            lat, lng, pedido.cliente_latitud, pedido.cliente_longitud
        )
        if distancia_km <= 1:  # menos de 1 km = "está por llegar"
            Notificacion.objects.create(
                usuario=pedido.venta.usuario,
                titulo='Tu pedido está cerca',
                mensaje=f'El repartidor está a menos de 1 km — Pedido #{pedido.id} 📍',
                tipo='info',
            )
            pedido.notificado_proximidad = True
            pedido.save(update_fields=['notificado_proximidad'])

    return JsonResponse({'ok': True})

@vista_dashboard
def api_pedidos_tiempo_real(request):
    """Estado en vivo de los últimos pedidos: repartidor asignado y avance de la entrega."""
    pedidos = (Pedido.objects
               .select_related('venta', 'venta__usuario', 'repartidor', 'repartidor__perfilemple')
               .prefetch_related('venta__detalles')
               .order_by('-fecha_creacion')[:20])

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
            'cliente_latitud': float(ped.cliente_latitud) if ped.cliente_latitud else None,
            'cliente_longitud': float(ped.cliente_longitud) if ped.cliente_longitud else None,
            'repartidor_latitud': float(perfil_repartidor.repartidor_latitud) if perfil_repartidor and perfil_repartidor.repartidor_latitud else None,
            'repartidor_longitud': float(perfil_repartidor.repartidor_longitud) if perfil_repartidor and perfil_repartidor.repartidor_longitud else None,
            'distancia_km': float(ped.distancia_km) if ped.distancia_km else None,
            'tiempo_estimado_min': ped.tiempo_estimado_min,
        })

    resumen = {
        'pendientes': sum(1 for p in lista if p['estado'] in ('pendiente', 'preparando')),
        'en_camino': sum(1 for p in lista if p['estado'] == 'en_camino'),
        'entregados': sum(1 for p in lista if p['estado'] == 'entregado'),
        'cancelados': sum(1 for p in lista if p['estado'] == 'cancelado'),
    }

    return JsonResponse({'pedidos': lista, 'resumen': resumen})

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

NOMINATIM_HEADERS = {
    "User-Agent": "LzApp/1.0 (contacto@lacteoszulianos.com)"  # Nominatim exige un User-Agent identificable
}

def buscar_direccion(request):
    """
    Autocompletado de direcciones (geocodificación directa).
    GET /usuarios/buscar-direccion/?q=carrera+70+medellin
    """
    query = request.GET.get("q", "").strip()

    if len(query) < 4:
        return JsonResponse({"resultados": []})

    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query,
                "format": "json",
                "addressdetails": 1,
                "limit": 5,
                "countrycodes": "co",  # restringe a Colombia; quita esta línea si algún día haces envíos internacionales
            },
            headers=NOMINATIM_HEADERS,
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return JsonResponse({"resultados": [], "error": "No se pudo consultar el servicio de direcciones"}, status=502)

    resultados = [
        {
            "direccion": item["display_name"],
            "lat": float(item["lat"]),
            "lon": float(item["lon"]),
        }
        for item in data
    ]
    return JsonResponse({"resultados": resultados})


def direccion_desde_coordenadas(request):
    """
    Geocodificación inversa: convierte lat/lon (ya capturados por GPS) en una
    dirección legible para que el usuario la confirme.
    GET /usuarios/direccion-desde-coordenadas/?lat=6.2442&lon=-75.5812
    """
    lat = request.GET.get("lat")
    lon = request.GET.get("lon")

    if not lat or not lon:
        return JsonResponse({"error": "Faltan coordenadas"}, status=400)

    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "addressdetails": 1},
            headers=NOMINATIM_HEADERS,
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return JsonResponse({"error": "No se pudo consultar el servicio de direcciones"}, status=502)

    direccion = data.get("display_name", "Dirección no encontrada")
    return JsonResponse({"direccion": direccion})