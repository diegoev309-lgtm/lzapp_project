from django.contrib import admin

from .models import ConfiguracionSeguridad, SesionActiva


@admin.register(ConfiguracionSeguridad)
class ConfiguracionSeguridadAdmin(admin.ModelAdmin):
    list_display = ('deteccion_inactividad_activa', 'minutos_inactividad', 'fecha_actualizacion')


@admin.register(SesionActiva)
class SesionActivaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'direccion_ip', 'user_agent', 'ultima_actividad', 'fecha_inicio')
    list_filter = ('usuario',)
    search_fields = ('usuario__username', 'direccion_ip', 'session_key')
