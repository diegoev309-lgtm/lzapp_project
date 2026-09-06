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


def _ruta_completa_osrm(lat1, lon1, lat2, lon2):
    """Igual que _distancia_osrm, pero además pide la geometría de la ruta
    (polyline codificada) para poder dibujarla en el mapa."""
    url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
    try:
        respuesta = requests.get(
            url, params={"overview": "full", "geometries": "polyline"}, timeout=6
        ).json()
        if respuesta.get("code") != "Ok":
            raise ValueError("OSRM no pudo calcular la ruta")

        ruta = respuesta["routes"][0]
        distancia_km = ruta["distance"] / 1000
        tiempo_min = round(ruta["duration"] / 60)
        polyline = ruta["geometry"]
        return distancia_km, tiempo_min, polyline

    except Exception:
        return _distancia_haversine_km(lat1, lon1, lat2, lon2), None, None


def obtener_ruta_completa(lat1, lon1, lat2, lon2):
    """
    Como obtener_distancia_km, pero además devuelve la polyline codificada
    de la ruta, para dibujarla en el mapa. Úsala solo cuando vayas a
    *guardar* la ruta (ej. al asignar repartidor a un pedido) — no en cada
    ping de GPS del repartidor, porque pedir la geometría completa es más
    pesado para el servidor demo de OSRM que solo pedir distancia/tiempo.
    """
    return _ruta_completa_osrm(lat1, lon1, lat2, lon2)


def obtener_direccion(lat, lng):
    """Dirección legible de unas coordenadas (Nominatim / OpenStreetMap).

    Se usa para rellenar el destino de un pedido que quedó solo con el pin:
    si el cliente marcó su ubicación con el GPS y la geocodificación del
    navegador no alcanzó a responder, el pedido llegaba sin texto y el
    repartidor veía "Sin dirección registrada" aunque el punto estuviera
    perfectamente puesto en el mapa.

    Devuelve None si el servicio no responde: es un dato de apoyo, las
    coordenadas siguen siendo la fuente real del destino.
    """
    try:
        respuesta = requests.get(
            'https://nominatim.openstreetmap.org/reverse',
            params={'format': 'json', 'lat': str(lat), 'lon': str(lng),
                    'accept-language': 'es'},
            headers={'User-Agent': 'LacteosZulianos/1.0'},
            # Timeout corto a propósito: esto corre dentro de la asignación,
            # que a su vez cuelga de los endpoints en vivo. Si Nominatim
            # está lento, vale más quedarse sin el texto de la dirección
            # (las coordenadas ya alcanzan para entregar) que dejar
            # esperando al repartidor mirando la pantalla.
            timeout=3,
        )
        return respuesta.json().get('display_name')
    except (requests.RequestException, ValueError):
        return None


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