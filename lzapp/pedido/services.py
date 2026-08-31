"""
Cálculo de distancia/tiempo entre dos coordenadas, usando OSRM
(Open Source Routing Machine) — servicio gratuito basado en
OpenStreetMap, sin necesidad de API key.

Si el servidor demo de OSRM falla o no responde (es un servicio
público compartido, sin garantía de disponibilidad 24/7), caemos
automáticamente a Haversine (línea recta) para no romper el flujo.
"""
import math
import requests


def _distancia_haversine_km(lat1, lon1, lat2, lon2):
    R = 6371  # radio de la Tierra en km
    lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _distancia_osrm(lat1, lon1, lat2, lon2):
    """OSRM espera las coordenadas en orden lon,lat (al revés de lo normal)."""
    url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
    try:
        respuesta = requests.get(url, params={"overview": "false"}, timeout=6).json()
        if respuesta.get("code") != "Ok":
            raise ValueError("OSRM no pudo calcular la ruta")

        ruta = respuesta["routes"][0]
        distancia_km = ruta["distance"] / 1000
        tiempo_min = round(ruta["duration"] / 60)
        return distancia_km, tiempo_min

    except Exception:
        return _distancia_haversine_km(lat1, lon1, lat2, lon2), None


def obtener_distancia_km(lat1, lon1, lat2, lon2):
    """
    Punto único de entrada para calcular distancia. Devuelve (distancia_km, tiempo_estimado_min).
    Cualquier parte del proyecto que necesite distancia debe llamar aquí,
    nunca directo a Haversine u OSRM.
    """
    return _distancia_osrm(lat1, lon1, lat2, lon2)


def obtener_repartidor_mas_cercano(cliente_lat, cliente_lng, candidatos):
    """
    candidatos: queryset/lista de PerfilEmple con repartidor_latitud/longitud ya cargados.
    Devuelve (perfil_emple_mas_cercano, distancia_km, tiempo_min) o (None, None, None).
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