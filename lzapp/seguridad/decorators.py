from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache


def staff_required(view_func):
    #"""
    #A diferencia de user_passes_test, distingue dos destinos: anónimo ->
    #login (con ?next=, para volver aquí tras loguearse); autenticado pero
    #sin is_staff/is_superuser -> 'client' con un mensaje (evita el loop
    #confuso de mandar a un cliente ya logueado de vuelta al formulario de
    #login que no necesita).
    #"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url=reverse('login'))
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, 'No tienes permiso para acceder a esa sección.')
            return redirect('client')
        return view_func(request, *args, **kwargs)
    return wrapper


def vista_dashboard(view_func):
    #"""never_cache + staff_required combinados: el decorador único que se
    #aplica a toda vista del panel administrativo. never_cache impide que el
    #navegador muestre una copia cacheada del dashboard al navegar con
    #atrás/adelante después de cerrar sesión; staff_required revalida en
    #cada request que la sesión siga siendo de un usuario staff/superuser."""
    return never_cache(staff_required(view_func))
