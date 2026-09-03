from django.contrib.auth.models import User
from django.db import models


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
