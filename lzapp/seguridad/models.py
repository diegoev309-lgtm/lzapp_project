from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class ConfiguracionSeguridad(models.Model):
    #"""
    #Fila única (pk=1) con la política de seguridad global del dashboard.
    #Editable desde el módulo Seguridad; obtener_configuracion() la crea con
    #valores por defecto si por alguna razón no existe.
    #"""

    deteccion_inactividad_activa = models.BooleanField(
        default=True,
        help_text='Si está activo, el staff se desloguea solo tras N minutos sin actividad.'
    )
    minutos_inactividad = models.PositiveIntegerField(
        default=15,
        help_text='Minutos de inactividad antes de cerrar la sesión automáticamente.'
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configuracion_seguridad'

    def __str__(self):
        estado = 'activa' if self.deteccion_inactividad_activa else 'inactiva'
        return f'Configuración de seguridad ({estado}, {self.minutos_inactividad} min)'


class SesionActiva(models.Model):
    #"""
    #Una fila por sesión de Django de un usuario logueado: permite mostrar
    #"mis dispositivos conectados" (estilo WhatsApp) y cerrarlos remotamente.
    #Se crea/actualiza vía signals.py (login/logout) y se refresca en cada
    #request autenticado desde middleware.py.
    #"""

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sesiones_activas')
    session_key = models.CharField(max_length=40, unique=True)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    # Sin auto_now: el middleware necesita leer el valor ANTERIOR antes de
    # pisarlo para decidir si la sesión ya estuvo inactiva demasiado tiempo.
    ultima_actividad = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'sesion_activa'
        ordering = ['-ultima_actividad']

    def __str__(self):
        return f'{self.usuario.username} · {self.session_key[:8]}… · {self.direccion_ip or "?"}'


class RegistroAuditoria(models.Model):
    #"""
    #Una fila por acción sensible hecha desde el panel administrativo
    #(eliminar/crear usuarios, cambios de configuración de seguridad, etc.).
    #actor queda en null si el usuario que la hizo se elimina después, para
    #no perder el historial de lo que pasó.
    #"""

    actor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='acciones_auditoria',
    )
    accion = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=255)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'registro_auditoria'
        ordering = ['-fecha']

    def __str__(self):
        quien = self.actor.username if self.actor else 'Sistema'
        return f'{quien} · {self.accion} · {self.fecha:%d/%m/%Y %H:%M}'
