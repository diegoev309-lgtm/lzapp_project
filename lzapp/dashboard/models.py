from django.db import models

#tabla de productos

class Producto(models.Model):
    nombre = models.CharField(max_length=100, null=True)
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock_actual = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=15)
    disponibilidad = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'producto'

    def __str__(self):
        return self.nombre

#tabla de produccion

class Produccion(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad_producida = models.PositiveIntegerField()
    fecha_produccion = models.DateTimeField(auto_now_add=True)
    observacion = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        nueva = self.pk is None
        super().save(*args, **kwargs)

        if nueva:
            self.producto.stock_actual += self.cantidad_producida
            self.producto.save()