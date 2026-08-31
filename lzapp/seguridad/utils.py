from .models import ConfiguracionSeguridad


def obtener_ip_cliente(request):
    #"""
    #Dato informativo (como el IP que muestra WhatsApp en "dispositivos
    #conectados"), NUNCA se usa para decisiones de acceso — por eso no
    #importa que X-Forwarded-For sea falseable por el cliente.
    #"""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def describir_dispositivo(user_agent):
    #"""
    #Parser casero, aproximado a propósito (igual que el de WhatsApp:
    #"Chrome en Windows" alcanza, no hace falta la versión exacta). No se
    #agrega ninguna librería nueva porque el proyecto no trackea
    #dependencias (no hay requirements.txt).
    #"""
    ua = (user_agent or '').lower()

    if 'iphone' in ua:
        so = 'iPhone'
    elif 'ipad' in ua:
        so = 'iPad'
    elif 'android' in ua:
        so = 'Android'
    elif 'windows' in ua:
        so = 'Windows'
    elif 'macintosh' in ua or 'mac os' in ua:
        so = 'Mac'
    elif 'linux' in ua:
        so = 'Linux'
    else:
        so = 'Dispositivo desconocido'

    if 'edg/' in ua:
        navegador = 'Edge'
    elif 'opr/' in ua or 'opera' in ua:
        navegador = 'Opera'
    elif 'chrome' in ua:
        navegador = 'Chrome'
    elif 'firefox' in ua:
        navegador = 'Firefox'
    elif 'safari' in ua:
        navegador = 'Safari'
    else:
        navegador = 'navegador desconocido'

    return f'{so} · {navegador}'


def obtener_configuracion():
    #"""Fila única (pk=1). La crea con valores por defecto si no existe."""
    config, _ = ConfiguracionSeguridad.objects.get_or_create(
        pk=1,
        defaults={'deteccion_inactividad_activa': True, 'minutos_inactividad': 15},
    )
    return config
