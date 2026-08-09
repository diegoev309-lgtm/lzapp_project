from django.contrib.auth.signals import user_logged_in
from django.db import IntegrityError
from django.dispatch import receiver
from django.utils import timezone


@receiver(user_logged_in)
def migrar_tirada_anonima_a_usuario(sender, request, user, **kwargs):
    #"""
    #Cuando un visitante anónimo que YA jugó la ruleta hoy inicia sesión,
    #reasignamos su TiradaDiaria de hoy (creada con sesion_key) al usuario
    #recién logueado, para que no pierda el premio ni pueda jugar de nuevo
    #con la cuenta. django.contrib.auth.login() dispara esta señal
    #automáticamente (usuarios/views.py ya la usa, no hace falta tocarlo).
    #
    #Si el usuario ya tenía su propia tirada de hoy por otra vía (poco
    #probable, pero posible), no rompemos el login: dejamos la tirada
    #anónima huérfana tal cual, sin reasignar.
    #"""
    from dashboard.models import TiradaDiaria  # import local: evita import circular al cargar la app

    session_key = getattr(request.session, 'session_key', None)
    if not session_key:
        return

    hoy = timezone.now().date()
    tirada_anonima = TiradaDiaria.objects.filter(
        sesion_key=session_key, fecha=hoy, usuario__isnull=True
    ).first()
    if not tirada_anonima:
        return

    tirada_anonima.usuario = user
    try:
        tirada_anonima.save(update_fields=['usuario'])
    except IntegrityError:
        # El usuario ya tenía su propia tirada de hoy (por otra sesión,
        # por ejemplo). No rompemos el login, simplemente no reasignamos.
        pass
