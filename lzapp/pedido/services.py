"""
Cálculo de distancia/tiempo entre dos coordenadas.

Hoy usa la fórmula de Haversine (línea recta) porque no tenemos el API
key de Google Maps. Cuando lo consigamos, solo hay que:

  1. Poner GOOGLE_MAPS_API_KEY en el .env
  2. Cambiar USAR_DISTANCE_MATRIX = True en settings.py

Nada más se toca — cualquier parte del proyecto que necesite distancia
(auto-asignación de repartidor, cálculo de ruta al crear un pedido,
etc.) siempre debe llamar a obtener_distancia_km(), nunca directamente
a Haversine o a Google.
"""
import math
import requests
from django.conf import settings


def _distancia_haversine_km(lat1, lon1, lat2, lon2):
    R = 6371  # radio de la Tierra en km
    lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _distancia_google_distance_matrix(lat1, lon1, lat2, lon2):
    """Distancia y tiempo REALES por carretera, vía Google Distance Matrix API."""
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": f"{lat1},{lon1}",
        "destinations": f"{lat2},{lon2}",
        "key": settings.GOOGLE_MAPS_API_KEY,
        "language": "es",
        "units": "metric",
    }
    try:
        respuesta = requests.get(url, params=params, timeout=5).json()
        elemento = respuesta["rows"][0]["elements"][0]
        if elemento["status"] != "OK":
            raise ValueError("Google no pudo calcular la ruta")

        distancia_km = elemento["distance"]["value"] / 1000
        tiempo_min = round(elemento["duration"]["value"] / 60)
        return distancia_km, tiempo_min

    except Exception:
        # Si Google falla (sin señal, timeout, dirección inválida, etc.)
        # no tronamos el flujo — caemos de vuelta a Haversine.
        return _distancia_haversine_km(lat1, lon1, lat2, lon2), None


def obtener_distancia_km(lat1, lon1, lat2, lon2):
    """
    Punto único de entrada para calcular distancia.
    Devuelve (distancia_km, tiempo_estimado_min).
    tiempo_estimado_min viene en None mientras se use Haversine, porque
    esa fórmula solo calcula distancia en línea recta, no tiempo real.
    """
    if getattr(settings, "USAR_DISTANCE_MATRIX", False) and settings.GOOGLE_MAPS_API_KEY:
        return _distancia_google_distance_matrix(lat1, lon1, lat2, lon2)

    return _distancia_haversine_km(lat1, lon1, lat2, lon2), None


def obtener_repartidor_mas_cercano(cliente_lat, cliente_lng, candidatos):
    """
    candidatos: queryset/lista de PerfilEmple con repartidor_latitud/longitud ya cargados.
    Devuelve (perfil_emple_mas_cercano, distancia_km, tiempo_min) o (None, None, None) si no hay candidatos.
    """
    mejor = None
    mejor_distancia = None
    mejor_tiempo = None

    for candidato in candidatos:
        distancia, tiempo = obtener_distancia_km(
            cliente_lat, cliente_lng,
            candidato.repartidor_latitud, candidato.repartidor_longitud,
        )
        if mejor_distancia is None or distancia < mejor_distancia:
            mejor_distancia, mejor_tiempo, mejor = distancia, tiempo, candidato

    return mejor, mejor_distancia, mejor_tiempo