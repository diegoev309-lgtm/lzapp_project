from django.contrib import admin
from dashboard.models import Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'titulo', 'mensaje', 'usuario', 'leida', 'fecha_creacion')
    list_filter = ('tipo', 'leida')
    search_fields = ('titulo', 'mensaje')