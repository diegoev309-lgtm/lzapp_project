from django.contrib import admin

from dashboard.models import ConfiguracionSeguridad, SesionActiva

from .models import RegistroAuditoria


@admin.register(ConfiguracionSeguridad)
class ConfiguracionSeguridadAdmin(admin.ModelAdmin):
    list_display = ('deteccion_inactividad_activa', 'minutos_inactividad', 'fecha_actualizacion')


@admin.register(SesionActiva)
class SesionActivaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'direccion_ip', 'user_agent', 'ultima_actividad', 'fecha_inicio')
    list_filter = ('usuario',)
    search_fields = ('usuario__username', 'direccion_ip', 'session_key')


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'actor', 'accion', 'descripcion', 'direccion_ip')
    list_filter = ('accion',)
    search_fields = ('actor__username', 'descripcion', 'direccion_ip')
    date_hierarchy = 'fecha'
