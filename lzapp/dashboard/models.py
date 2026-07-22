from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


#tabla auth_user con telefono y nameuser

class Perfil(models.Model):
    usuario = models.OneToOneField(User,on_delete=models.CASCADE)
    telefono = models.CharField(max_length=15)

    def __str__(self):
        return self.usuario.username

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
        
    @property
    def ratio_stock(self):
        """Qué tan por encima está del mínimo. >1 = sobra stock, hay que venderlo ya."""
        if self.stock_minimo == 0:
            return float(self.stock_actual)
        return self.stock_actual / self.stock_minimo

    def __str__(self):
        return self.nombre

# tablas de descuentos

class ReglaDescuentoAutomatico(models.Model):
    nombre = models.CharField(max_length=100)
    activa = models.BooleanField(default=True)
    prioridad = models.PositiveIntegerField(default=0)  # mayor = se evalúa primero

    # Condiciones (deja en None/0 la que no quieras usar en esta regla)
    dias_sin_venderse_min = models.PositiveIntegerField(null=True, blank=True)
    stock_multiplicador_min = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True,
        help_text="Ej: 1.5 = se activa si stock_actual >= stock_minimo * 1.5"
    )
    dias_antes_vencimiento_max = models.PositiveIntegerField(null=True, blank=True)

    descuento_porcentaje = models.PositiveIntegerField()

    class Meta:
        ordering = ['-prioridad']

    def aplica_a(self, producto):
        condiciones = []
        if self.dias_sin_venderse_min and producto.fecha_ultimo_movimiento_stock:
            dias = (timezone.now() - producto.fecha_ultimo_movimiento_stock).days
            condiciones.append(dias >= self.dias_sin_venderse_min)
        if self.stock_multiplicador_min:
            condiciones.append(
                producto.stock_actual >= producto.stock_minimo * float(self.stock_multiplicador_min)
            )
        if self.dias_antes_vencimiento_max and producto.fecha_vencimiento:
            dias_restantes = (producto.fecha_vencimiento - timezone.now().date()).days
            condiciones.append(0 <= dias_restantes <= self.dias_antes_vencimiento_max)
        return any(condiciones)  # o all(condiciones) si quieres que TODAS se cumplan
    
class Descuento(models.Model):
    ORIGEN = [('manual', 'Manual'), ('automatico', 'Automático')]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='descuentos')
    porcentaje = models.PositiveIntegerField()
    origen = models.CharField(max_length=20, choices=ORIGEN, default='manual')
    regla = models.ForeignKey(ReglaDescuentoAutomatico, null=True, blank=True, on_delete=models.SET_NULL)

    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha_inicio']

    def esta_vigente(self):
        if not self.activo:
            return False
        if self.fecha_fin and timezone.now() > self.fecha_fin:
            return False
        return True

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