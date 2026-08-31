from .utils import obtener_configuracion


def configuracion_seguridad(request):
    #"""
    #Solo para staff/superuser autenticado: expone la config para que
    #masterpage_dashboard.html arme el temporizador de inactividad en JS.
    #Vacío para cualquier otro caso (incluyendo clientes logueados), así el
    #atributo data-seguridad-activa nunca se emite fuera del dashboard.
    #"""
    usuario = request.user
    if not usuario.is_authenticated or not (usuario.is_staff or usuario.is_superuser):
        return {}
    return {'config_seguridad': obtener_configuracion()}
