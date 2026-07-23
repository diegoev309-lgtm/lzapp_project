from django.db import models
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.models import User


#tabla auth_user con telefono

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
    fecha_ultimo_movimiento_stock = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'producto'

    def __str__(self):
        return self.nombre

    #Sirve para darle propiedades a los models para hacer  

    @property
    def ratio_stock(self):
        """Qué tan por encima está del mínimo. >1 = sobra stock, hay que venderlo ya."""
        if self.stock_minimo == 0:
            return float(self.stock_actual)
        return self.stock_actual / self.stock_minimo

    def descuento_vigente(self):
        return(self.descuentos.filter(activo=True).order_by("-fecha_inicio").first())
    
    def precio_con_descuento(self):
        descuento = self.descuento_vigente
        if descuento:
            return self.precio * (Decimal(100 - descuento.porcentaje) / Decimal(100))
        return self.precio
    
# tablas de descuentos

class ReglaDescuentoAutomatico(models.Model):
    TIPO_CONDICION = (('OR', 'Cumplir cualquiera'),('AND', 'Cumplir todas'),)

    nombre = models.CharField(max_length=100)
    activa = models.BooleanField(default=True)
    prioridad = models.PositiveIntegerField(default=0,help_text="Las reglas con mayor prioridad se evalúan primero.")
    tipo_condicion = models.CharField(max_length=3,choices=TIPO_CONDICION,default='OR',help_text="Determina si debe cumplirse una o todas las condiciones.")

    # ===== CONDICIONES =====

    stock_multiplicador_min = models.DecimalField(max_digits=4,decimal_places=2,null=True,blank=True,help_text="Ejemplo: 2.0 significa que el stock actual debe ser al menos el doble del stock mínimo.")

    # Se deja para futuras versiones (cuando exista el módulo de lotes)
    dias_antes_vencimiento = models.PositiveIntegerField(null=True,blank=True,help_text="Disponible cuando se implemente el control de vencimientos.")

    # ===== DESCUENTO =====

    descuento_porcentaje = models.PositiveIntegerField()

    class Meta:
        db_table = "regla_descuento_automatico"
        ordering = ['-prioridad']

    def __str__(self):
        return f"{self.nombre} ({self.descuento_porcentaje}%)"
    
from django.db import models
from django.utils import timezone



class Descuento(models.Model):
    ORIGEN = (('manual', 'Manual'),('automatico', 'Automático'),)

    producto = models.ForeignKey(Producto,on_delete=models.CASCADE,related_name='descuentos')
    porcentaje = models.PositiveIntegerField()
    origen = models.CharField(max_length=20,choices=ORIGEN,default='manual')
    regla = models.ForeignKey(ReglaDescuentoAutomatico,null=True,blank=True,on_delete=models.SET_NULL)
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_fin = models.DateTimeField(null=True,blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "descuento"
        ordering = ['-fecha_inicio']

    def esta_vigente(self):
        ahora = timezone.now()
        if not self.activo:
            return False
        if self.fecha_inicio > ahora:
            return False
        if self.fecha_fin and ahora > self.fecha_fin:
            return False
        return True

    def __str__(self):
        return f"{self.producto.nombre} - {self.porcentaje}%"

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