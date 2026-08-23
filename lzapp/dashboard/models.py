from django.contrib.auth.models import User
from django.db import models
from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg, Count

import random
import string


#tabla auth_user con telefono

class Perfil(models.Model):
    usuario = models.OneToOneField(User,on_delete=models.CASCADE)
    telefono = models.CharField(max_length=15)
    direccion = models.CharField(max_length=255, blank=True, null=True) 

    class Meta:
        db_table = 'perfil'

    def __str__(self):
        return self.usuario.username

class PerfilEmple(models.Model):
    empleado = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    rol = models.CharField(
        max_length=20,
        choices=[
            ('cliente', 'Cliente'),
            ('empleado', 'Empleado'),
        ],
        default='cliente'
    )


#tabla de productos

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock_actual = models.PositiveIntegerField(default=0, null=True)
    stock_minimo = models.PositiveIntegerField(default=15, null=True)
    disponibilidad = models.BooleanField(default=True, null=True)
    fecha_vencimiento = models.DateField(
        null=True, blank=True,
        help_text='Fecha de vencimiento del lote actual (se carga manualmente). '
                   'Se usa solo como sugerencia visual al armar campañas de descuento.'
    )
    fecha_registro = models.DateTimeField(auto_now_add=True, null=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True, null=True)

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

    class Meta:
        db_table = 'produccion'

    def save(self, *args, **kwargs):
        nueva = self.pk is None
        super().save(*args, **kwargs)

        if nueva:
            self.producto.stock_actual += self.cantidad_producida
            self.producto.save()



# =========================================================
# 1) HISTORIAL DE VENTAS (no existía, lo necesitamos como
#    base para saber qué compró y qué NO compró cada cliente)
# =========================================================

class Venta(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ventas')
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    mp_payment_id = models.CharField(max_length=50, unique=True, null=True, blank=True)

    class Meta:
        db_table = 'venta'
        ordering = ['-fecha']

    def __str__(self):
        return f'Venta #{self.pk} - {self.usuario.username}'


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'detalle_venta'

    def save(self, *args, **kwargs):
        if not self.subtotal:
            self.subtotal = self.precio_unitario * self.cantidad
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.producto.nombre} x{self.cantidad}'


# =========================================================
# 1.1) PEDIDO — seguimiento de entrega, independiente de la Venta
#      (una Venta es la transacción/pago; un Pedido es su reparto:
#      estado, repartidor, incidencias, etc. Separado a propósito
#      para poder crecer -ruta, fotos de entrega, firma, tiempos-
#      sin tocar la tabla de ventas/pagos)
# =========================================================

class Pedido(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE  = 'pendiente',  'Pendiente'
        PREPARANDO = 'preparando', 'Preparando'
        EN_CAMINO  = 'en_camino',  'En camino'
        ENTREGADO  = 'entregado',  'Entregado'
        CANCELADO  = 'cancelado',  'Cancelado'

    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, related_name='pedido')

    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    repartidor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='entregas_asignadas',
        help_text='Empleado encargado de repartir este pedido'
    )
    direccion_entrega = models.CharField(max_length=255, blank=True, null=True)
    incidencia = models.CharField(
        max_length=255, blank=True, null=True,
        help_text='Problema reportado en el pedido (retraso, producto dañado, cliente ausente, etc.)'
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pedido'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'Pedido #{self.pk} (Venta #{self.venta_id}) - {self.get_estado_display()}'


from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=Venta)
def crear_pedido_automatico(sender, instance, created, **kwargs):
    """Cada Venta nueva obtiene automáticamente su Pedido de seguimiento."""
    if created:
        Pedido.objects.get_or_create(venta=instance)


# =========================================================
# 2) CAMPAÑA DE DESCUENTO (lo que TÚ configuras/manipulas)
# =========================================================

class CampanaDescuento(models.Model):

    class Frecuencia(models.TextChoices):
        SEMANAL = 'SEMANAL', 'Semanal'
        MENSUAL = 'MENSUAL', 'Mensual'
        UNICA = 'UNICA', 'Única vez'

    nombre = models.CharField(max_length=120)
    productos = models.ManyToManyField(
        Producto,
        related_name='campanas_descuento',
        help_text='Quesos/productos que se quieren mover'
    )

    porcentaje_descuento = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text='Ej: 20.00 para 20% de descuento'
    )

    # ---- criterio de selección de clientes ----
    dias_sin_compra = models.PositiveIntegerField(
        default=30,
        help_text='Se elige entre clientes que no han comprado este producto '
                   'en los últimos X días (o nunca lo han comprado).'
    )
    cantidad_clientes = models.PositiveIntegerField(
        default=10,
        help_text='Tope preferido de clientes "ganadores" por ejecución. '
                   'El límite real será el menor entre esto, el stock disponible '
                   'y el porcentaje_maximo_clientes.'
    )
    porcentaje_maximo_clientes = models.DecimalField(
        max_digits=5, decimal_places=2, default=10,
        help_text='Tope como % del total de clientes activos que pueden recibir '
                   'el premio en UNA sola ejecución (ej: 10.00 = máx 10% de la base). '
                   'Evita saturar de descuentos y controla el consumo de memoria/consultas.'
    )
    stock_reservado_no_ofertable = models.PositiveIntegerField(
        default=0,
        help_text='Unidades de stock que NO se cuentan como disponibles para oferta '
                   '(colchón extra por encima del stock_minimo del producto).'
    )

    # ---- vigencia del premio individual ----
    dias_validez_premio = models.PositiveIntegerField(
        default=7,
        help_text='Cuántos días dura activo el premio para el cliente que lo ganó'
    )

    # ---- control de encendido/apagado, fácil y manipulable ----
    frecuencia = models.CharField(max_length=10, choices=Frecuencia.choices, default=Frecuencia.SEMANAL)
    activo = models.BooleanField(default=True, help_text='Apágalo para pausar la campaña sin borrarla')
    fecha_inicio = models.DateField(default=timezone.now)
    fecha_fin = models.DateField(null=True, blank=True, help_text='Vacío = sin fecha de fin')

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ultima_ejecucion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'campana_descuento'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'{self.nombre} ({self.get_frecuencia_display()})'

    def esta_vigente(self):
        hoy = timezone.now().date()
        if not self.activo:
            return False
        if hoy < self.fecha_inicio:
            return False
        if self.fecha_fin and hoy > self.fecha_fin:
            return False
        return True

    def debe_ejecutarse(self):
        """Decide si toca correr el sorteo hoy, según la frecuencia."""
        if not self.esta_vigente():
            return False
        if not self.ultima_ejecucion:
            return True
        dias_desde_ultima = (timezone.now() - self.ultima_ejecucion).days
        if self.frecuencia == self.Frecuencia.SEMANAL:
            return dias_desde_ultima >= 7
        if self.frecuencia == self.Frecuencia.MENSUAL:
            return dias_desde_ultima >= 30
        if self.frecuencia == self.Frecuencia.UNICA:
            return False  # ya se ejecutó una vez
        return False


# =========================================================
# 3) EL "PREMIO" GANADO POR CADA CLIENTE
# =========================================================

def generar_codigo():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


class DescuentoAsignado(models.Model):
    campana = models.ForeignKey(CampanaDescuento, on_delete=models.CASCADE, related_name='asignaciones')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='descuentos_ganados')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)

    codigo = models.CharField(max_length=10, unique=True, default=generar_codigo)

    precio_original = models.DecimalField(max_digits=10, decimal_places=2)
    precio_con_descuento = models.DecimalField(max_digits=10, decimal_places=2)

    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField()

    mostrado = models.BooleanField(default=False, help_text='Si ya se le mostró la tarjeta/animación de premio')
    usado = models.BooleanField(default=False)
    fecha_uso = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'descuento_asignado'
        ordering = ['-fecha_asignacion']
        constraints = [
            models.UniqueConstraint(
                fields=['campana', 'usuario', 'producto'],
                name='un_premio_por_cliente_por_campana'
            )
        ]

    def __str__(self):
        return f'{self.usuario.username} -> {self.producto.nombre} ({self.codigo})'

    def esta_activo(self):
        return (not self.usado) and timezone.now() <= self.fecha_expiracion

    def marcar_usado(self):
        self.usado = True
        self.fecha_uso = timezone.now()
        self.save(update_fields=['usado', 'fecha_uso'])


class Calificacion(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='calificaciones')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calificaciones_hechas')
    puntaje = models.PositiveSmallIntegerField(
        choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]
    )
    fecha = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'calificacion'
        constraints = [
            models.UniqueConstraint(fields=['producto', 'usuario'], name='una_calificacion_por_usuario_por_producto')
        ]

    def __str__(self):
        return f'{self.usuario.username} -> {self.producto.nombre}: {self.puntaje}★'


# =========================================================
# JUEGO DIARIO ("Ruleta del día") 
# =========================================================

class TiradaDiaria(models.Model):
    #"""
    #Una tirada por usuario (o por sesión, si es anónimo) por día. El
    #resultado sale de la tabla fija de probabilidades en services.py
    #(NO configurable desde el dashboard). fecha_expiracion replica la
    #misma idea de vigencia de 7 días que ya usa DescuentoAsignado.
    #"""

    class Resultado(models.TextChoices):
        SIGUE_INTENTANDO = 'SIGUE_INTENTANDO', 'Sigue intentando'
        CUPON_5 = 'CUPON_5', 'Cupón 5% próxima compra'
        ENVIO_GRATIS = 'ENVIO_GRATIS', 'Envío gratis'
        BOLETO_DORADO = 'BOLETO_DORADO', 'Boleto dorado'

    usuario = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.CASCADE, related_name='tiradas_diarias'
    )
    # Solo se usa cuando la tirada es de un visitante anónimo (usuario=None).
    sesion_key = models.CharField(max_length=40, null=True, blank=True)

    fecha = models.DateField(auto_now_add=True)
    resultado = models.CharField(max_length=20, choices=Resultado.choices)

    reclamado = models.BooleanField(default=False, help_text='Si ya se aplicó el efecto del premio (cupón/envío/boleto).')
    # Evita que un mismo "boleto dorado" siga colando al usuario al pool de
    # elegibles en TODAS las ejecuciones futuras de campaña: una vez que
    # quedó incluido en el pool de algún producto de UNA ejecución (haya
    # ganado o no), se marca aquí y deja de aplicar.
    boleto_usado = models.BooleanField(default=False)

    fecha_expiracion = models.DateTimeField()

    class Meta:
        db_table = 'tirada_diaria'
        ordering = ['-fecha', '-id']
        constraints = [
            # MySQL no soporta UniqueConstraint(condition=...) (índices únicos
            # condicionales/parciales), solo Postgres/SQLite. Con DOS
            # constraints normales logramos el mismo efecto: tanto MySQL como
            # Postgres tratan cada NULL como distinto en un índice único, así
            # que un usuario logueado (sesion_key=NULL) nunca choca con las
            # filas anónimas (usuario=NULL), y viceversa.
            models.UniqueConstraint(fields=['usuario', 'fecha'], name='una_tirada_por_usuario_por_dia'),
            models.UniqueConstraint(fields=['sesion_key', 'fecha'], name='una_tirada_por_sesion_por_dia'),
        ]

    def __str__(self):
        quien = self.usuario.username if self.usuario else f'anon:{self.sesion_key}'
        return f'{quien} - {self.fecha} - {self.get_resultado_display()}'

    def esta_vigente(self):
        return timezone.now() <= self.fecha_expiracion
