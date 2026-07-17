from django.db import models

class Usuario(models.Model):

    nombre = models.CharField(max_length=100)
    correo = models.EmailField(unique=True)
    contraseña = models.CharField(max_length=255)
    telefono = models.CharField(max_length=15)

    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre