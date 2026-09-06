from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

import random
import string
import hashlib

# =========================================================
# #Tabla de usuarios
# =========================================================

class Perfil(models.Model):
    usuario = models.OneToOneField(User,on_delete=models.CASCADE)
    telefono = models.CharField(max_length=20)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    foto = models.ImageField(upload_to='perfiles/', blank=True, null=True)

    class Meta:
        db_table = 'perfil'

    def __str__(self):
        return self.usuario.username

# =========================================================
# #Tabla de empleados
# =========================================================

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
    class Vehiculo(models.TextChoices):
        MOTO      = 'moto',      'Moto'
        BICICLETA = 'bicicleta', 'Bicicleta'
        CARRO     = 'carro',     'Carro'
        A_PIE     = 'a_pie',     'A pie'

    repartidor_latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    repartidor_longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Arranca apagado a propósito: un repartidor está disponible solo
    # cuando ÉL le da a "Empezar a repartir". Con default=True el sistema
    # le asignaba entregas a gente que ni había salido de su casa.
    disponible = models.BooleanField(
        default=False,
        help_text='Lo enciende el propio repartidor al empezar su turno. '
                  'Solo los disponibles reciben entregas.'
    )
    vehiculo = models.CharField(
        max_length=15, choices=Vehiculo.choices, default=Vehiculo.MOTO,
        help_text='En qué reparte. Define cuánto puede cargar de una salida.'
    )
    capacidad_productos = models.PositiveIntegerField(
        default=20,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
        help_text='Cuántas unidades de producto le caben en el vehículo. '
                  'El sistema no le asigna entregas que no le quepan.'
    )
    ubicacion_actualizada = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.empleado.username} ({self.get_vehiculo_display()}, {self.capacidad_productos} u.)'

# =========================================================
# #Tabla de producto
# =========================================================

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    imagen_hash = models.CharField(max_length=32, blank=True, null=True, db_index=True, editable=False)
    precio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    stock_actual = models.PositiveIntegerField(
        default=0, null=True, blank=True,
        validators=[MaxValueValidator(100_000)],
    )
    stock_minimo = models.PositiveIntegerField(
        default=15, null=True, blank=True,
        validators=[MaxValueValidator(100_000)],
    )
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

    def save(self, *args, **kwargs):
        if self.imagen and hasattr(self.imagen, 'file'):
            try:
                self.imagen.seek(0)
                self.imagen_hash = hashlib.md5(self.imagen.read()).hexdigest()
                self.imagen.seek(0)
            except (ValueError, FileNotFoundError):
                pass
        elif not self.imagen:
            self.imagen_hash = None
        super().save(*args, **kwargs)

# =========================================================
# #Tabla de produccion
# =========================================================

class Produccion(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='lotes')
    cantidad_producida = models.PositiveIntegerField(validators=[MaxValueValidator(100_000)])
    cantidad_disponible = models.PositiveIntegerField(default=0, editable=False)
    fecha_vencimiento = models.DateField(help_text='Fecha de vencimiento de este lote específico.')
    fecha_produccion = models.DateTimeField(auto_now_add=True)
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'produccion'
        ordering = ['-fecha_produccion']

    def save(self, *args, **kwargs):
        nueva = self.pk is None
        if nueva:
            self.cantidad_disponible = self.cantidad_producida

        super().save(*args, **kwargs)

        if nueva:
            self.producto.stock_actual = (self.producto.stock_actual or 0) + self.cantidad_producida
            self._sincronizar_vencimiento()
            self.producto.save(update_fields=['stock_actual', 'fecha_vencimiento'])
            self.producto.stock_actual += self.cantidad_producida

        # El "vencimiento del lote actual" que se muestra en la tienda
        # siempre refleja el lote más próximo a vencer entre todos los
        # lotes registrados de este producto (no simplemente el último
        # que se cargó), para que la fecha sea útil de verdad.
        proximo_vencimiento = (
            Produccion.objects
            .filter(producto=self.producto, fecha_vencimiento__isnull=False)
            .order_by('fecha_vencimiento')
            .values_list('fecha_vencimiento', flat=True)
            .first()
        )
        self.producto.fecha_vencimiento = proximo_vencimiento
        self.producto.save()

    def _sincronizar_vencimiento(self):
        """El 'próximo vencimiento' del producto es el del lote vigente
        más cercano a vencer (FEFO), calculado siempre a partir de los
        lotes reales, nunca escrito a mano."""
        proximo = (
            Produccion.objects
            .filter(producto=self.producto, cantidad_disponible__gt=0)
            .order_by('fecha_vencimiento')
            .values_list('fecha_vencimiento', flat=True)
            .first()
        )
        self.producto.fecha_vencimiento = proximo



def descontar_stock_fefo(producto, cantidad):
    """Descuenta stock de los lotes más próximos a vencer primero.
    Llama a esto donde hoy confirmes una venta (donde se crea DetalleVenta)."""
    from django.db import transaction

    with transaction.atomic():
        lotes = (
            Produccion.objects
            .select_for_update()
            .filter(producto=producto, cantidad_disponible__gt=0)
            .order_by('fecha_vencimiento')
        )
        restante = cantidad
        for lote in lotes:
            if restante <= 0:
                break
            usar = min(lote.cantidad_disponible, restante)
            lote.cantidad_disponible -= usar
            lote.save(update_fields=['cantidad_disponible'])
            restante -= usar

        if restante > 0:
            raise ValueError(f'Stock insuficiente para {producto.nombre}')

        producto.stock_actual = max(0, (producto.stock_actual or 0) - cantidad)
        producto.fecha_vencimiento = (
            Produccion.objects
            .filter(producto=producto, cantidad_disponible__gt=0)
            .order_by('fecha_vencimiento')
            .values_list('fecha_vencimiento', flat=True)
            .first()
        )
        producto.save(update_fields=['stock_actual', 'fecha_vencimiento'])

# =========================================================
# #Tabla de ventas
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

# =========================================================
# #Tabla de detalles para las ventas
# =========================================================

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
# #Tabla de pedidos
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
    cliente_latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    cliente_longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    distancia_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    tiempo_estimado_min = models.PositiveIntegerField(null=True, blank=True)
    ruta_polyline = models.TextField(
        null=True, blank=True,
        help_text='Ruta codificada que devuelve Directions API, para no recalcularla cada vez'
    )
    incidencia = models.CharField(
        max_length=255, blank=True, null=True,
        help_text='Problema reportado en el pedido (retraso, producto dañado, cliente ausente, etc.)'
    )
    minutos_extra_incidencia = models.PositiveIntegerField(
        default=0,
        help_text='Demora extra por la incidencia. Se suma al tiempo estimado que ve el cliente.'
    )
    notificado_proximidad = models.BooleanField(
        default=False,
        help_text='Evita mandar la notificación de "está cerca" más de una vez'
    )
    codigo_entrega = models.CharField(
        max_length=4, blank=True, null=True,
        help_text='PIN de 4 dígitos que el cliente muestra y el repartidor '
                   'escribe para confirmar que entregó el pedido correcto.'
    )
    orden_en_ruta = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Puesto de este pedido dentro de la ruta del repartidor '
                  '(1 = la próxima parada). Es lo que le permite al cliente '
                  'ver cuántas entregas van antes de la suya.'
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
    """Cada Venta nueva obtiene automáticamente su Pedido de seguimiento.

    Nace directamente en PREPARANDO: apenas el pago queda aprobado la
    producción arranca, sin esperar a que nadie apruebe nada a mano. El
    estado PENDIENTE es la cola *posterior* a la preparación (pedido ya
    listo esperando repartidor), no un paso previo — si fuera previo, la
    cocina se quedaría frenada esperando un clic del admin.

    El pedido nace con la ubicación que el cliente tiene registrada en su
    perfil: así ningún pedido queda sin destino aunque el checkout no haya
    alcanzado a mandar el pin (y sin destino no se puede asignar
    repartidor, ni calcular ruta, ni dibujar nada en el mapa). Si el
    checkout sí manda un pin, después lo sobreescribe con ese.
    """
    if not created:
        return

    perfil = Perfil.objects.filter(usuario=instance.usuario).first()
    valores = {'estado': Pedido.Estado.PREPARANDO}
    if perfil and perfil.latitud and perfil.longitud:
        valores.update({
            'cliente_latitud': perfil.latitud,
            'cliente_longitud': perfil.longitud,
            'direccion_entrega': perfil.direccion,
        })

    Pedido.objects.get_or_create(venta=instance, defaults=valores)


from datetime import timedelta

# La asignación de repartidor y el avance de estados viven en
# pedido/asignacion.py (el motor), no en una señal: un pedido recién
# creado siempre está PREPARANDO y no se despacha hasta que termina su
# preparación, así que no hay nada que hacer en el post_save. El motor lo
# empujan los endpoints en vivo que los tres paneles ya consultan.

# =========================================================
# #Tabla de pedidos con un hostorial
# =========================================================

class HistorialEstadoPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='historial')
    estado = models.CharField(max_length=20, choices=Pedido.Estado.choices)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'historial_estado_pedido'
        ordering = ['fecha']

    def __str__(self):
        return f'Pedido #{self.pedido_id} -> {self.get_estado_display()} ({self.fecha:%d/%m %H:%M})'


@receiver(post_save, sender=Pedido)
def registrar_historial_estado(sender, instance, created, **kwargs):
    """Cada vez que el pedido se crea o cambia de estado, queda una fila
    en el historial — es lo que alimenta el timeline de seguimiento."""
    # -id además de -fecha: dos filas creadas en el mismo save() en
    # cascada (esta señal dispara otro save() más abajo para el PIN de
    # entrega) pueden quedar con el mismo timestamp si la resolución del
    # reloj del sistema es baja -- sin el desempate, "-fecha" solo podía
    # devolver cualquiera de las dos indistintamente.
    ultimo = instance.historial.order_by('-fecha', '-id').first()
    if created or not ultimo or ultimo.estado != instance.estado:
        HistorialEstadoPedido.objects.create(pedido=instance, estado=instance.estado)

        # Apenas sale a ruta se genera el PIN que el cliente le muestra al
        # repartidor para confirmar la entrega. Se genera una sola vez por
        # pedido (si ya lo tenía, por ejemplo al reabrirlo, se conserva).
        if instance.estado == Pedido.Estado.EN_CAMINO and not instance.codigo_entrega:
            instance.codigo_entrega = f'{random.randint(0, 9999):04d}'
            instance.save(update_fields=['codigo_entrega'])

MENSAJES_ESTADO_CLIENTE = {
    Pedido.Estado.PREPARANDO: ('Tu pedido está en preparación 👨‍🍳', 'info'),
    Pedido.Estado.PENDIENTE:  ('Tu pedido ya está listo y espera repartidor 📦', 'info'),
    Pedido.Estado.EN_CAMINO:  ('¡Tu pedido salió para entrega! 🚚', 'info'),
    Pedido.Estado.ENTREGADO:  ('Tu pedido fue entregado ✅', 'success'),
    Pedido.Estado.CANCELADO:  ('Tu pedido fue cancelado', 'warning'),
}

@receiver(post_save, sender=HistorialEstadoPedido)
def notificar_cambio_estado(sender, instance, created, **kwargs):
    """Cada fila nueva del historial (o sea, cada cambio real de estado)
    avisa a los tres lados del pedido: el cliente que lo espera, el admin
    que lo tiene que preparar y el repartidor que lo va a llevar."""
    if not created:
        return

    pedido = instance.pedido
    datos = MENSAJES_ESTADO_CLIENTE.get(instance.estado)
    if not datos:
        return

    mensaje, tipo = datos
    config = obtener_configuracion_entrega()
    minutos = config.minutos_preparacion

    # --- Cliente ---
    detalle = ''
    if instance.estado == Pedido.Estado.PREPARANDO:
        detalle = f' Tiempo estimado de preparación: {minutos} min.'
    elif instance.estado == Pedido.Estado.EN_CAMINO and pedido.orden_en_ruta:
        # El repartidor puede llevar varias entregas en la misma salida: el
        # cliente ve cuántas van antes de la suya para que el tiempo tenga
        # sentido en vez de parecer que se atrasó sin explicación.
        antes = pedido.orden_en_ruta - 1
        if antes > 0:
            plural = 's' if antes > 1 else ''
            detalle = f' Hay {antes} entrega{plural} antes de la tuya.'

    Notificacion.objects.create(
        usuario=pedido.venta.usuario,
        titulo='Actualización de tu pedido',
        mensaje=f'{mensaje} — Pedido #{pedido.id}.{detalle}',
        tipo=tipo,
        url='/pedido/mi-pedido',
    )

    # --- Admin: entró un pedido nuevo a producción ---
    if instance.estado == Pedido.Estado.PREPARANDO:
        for staff in User.objects.filter(is_staff=True, is_active=True):
            Notificacion.objects.create(
                usuario=staff,
                titulo='Pedido para preparar',
                mensaje=f'El pedido #{pedido.id} entró en preparación ({minutos} min estimados).',
                tipo='warning',
                url='/pedido/Pedidos',
            )
        return

    # --- Repartidor: recién acá se le asignó la entrega ---
    if instance.estado == Pedido.Estado.EN_CAMINO and pedido.repartidor_id:
        puesto = f' Es tu parada #{pedido.orden_en_ruta}.' if pedido.orden_en_ruta else ''
        Notificacion.objects.create(
            usuario_id=pedido.repartidor_id,
            titulo='Entrega asignada',
            mensaje=f'Te asignaron el pedido #{pedido.id}.{puesto}',
            tipo='info',
            url='/pedido/mis-entregas',
        )

# =========================================================
# #Tabla de notificaciones
# =========================================================

class Notificacion(models.Model):
    """
    Historial de avisos para el equipo administrador (bajo stock, productos
    guardados incompletos, etc.). Se muestran como 'toast' al momento de
    generarse y quedan aquí guardadas para el menú desplegable de la campana.
    """
 
    TIPO_CHOICES = [
        ('info', 'Información'),
        ('success', 'Éxito'),
        ('warning', 'Advertencia'),
        ('error', 'Error'),
    ]
 
    # Si es null, se considera una notificación general para todo el
    # equipo administrador (no asociada a un usuario en particular).
    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True,
        related_name='notificaciones'
    )
    titulo = models.CharField(max_length=120, blank=True)
    mensaje = models.CharField(max_length=255)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='info')
    url = models.CharField(
        max_length=255, blank=True,
        help_text='Enlace opcional al que lleva la notificación al hacer clic.'
    )
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        db_table = 'notificacion'
        ordering = ['-fecha_creacion']
 
    def __str__(self):
        return f'[{self.tipo}] {self.mensaje[:40]}'
 
    ICONOS_POR_TIPO = {
        'info': 'bi-info-circle-fill',
        'success': 'bi-check-circle-fill',
        'warning': 'bi-exclamation-triangle-fill',
        'error': 'bi-x-circle-fill',
    }
 
    @property
    def icono(self):
        return self.ICONOS_POR_TIPO.get(self.tipo, 'bi-bell-fill')

# =========================================================
# #Tabla de Campañas descuentos
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
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100'))],
        help_text='Ej: 20.00 para 20% de descuento'
    )

    # ---- criterio de selección de clientes ----
    dias_sin_compra = models.PositiveIntegerField(
        default=30,
        validators=[MaxValueValidator(3650)],
        help_text='Se elige entre clientes que no han comprado este producto '
                   'en los últimos X días (o nunca lo han comprado).'
    )
    cantidad_clientes = models.PositiveIntegerField(
        default=10,
        validators=[MaxValueValidator(100_000)],
        help_text='Tope preferido de clientes "ganadores" por ejecución. '
                   'El límite real será el menor entre esto, el stock disponible '
                   'y el porcentaje_maximo_clientes.'
    )
    porcentaje_maximo_clientes = models.DecimalField(
        max_digits=5, decimal_places=2, default=10,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text='Tope como % del total de clientes activos que pueden recibir '
                   'el premio en UNA sola ejecución (ej: 10.00 = máx 10% de la base). '
                   'Evita saturar de descuentos y controla el consumo de memoria/consultas.'
    )
    stock_reservado_no_ofertable = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(100_000)],
        help_text='Unidades de stock que NO se cuentan como disponibles para oferta '
                   '(colchón extra por encima del stock_minimo del producto).'
    )

    # ---- vigencia del premio individual ----
    dias_validez_premio = models.PositiveIntegerField(
        default=7,
        validators=[MaxValueValidator(365)],
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

# =========================================================
# #Tabla de campañas para asignar los descuentos
# =========================================================

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

# =========================================================
# #Tabla de calificacion de productos
# =========================================================

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
# #Tabla de tirada diaria 
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


# =========================================================
# #Configuración de premios de la ruleta diaria (dashboard)
# =========================================================

class PremioRuletaDiaria(models.Model):
    #"""
    #Activa/desactiva y ajusta el peso (%) de los premios de la ruleta
    #diaria que SÍ son configurables desde el dashboard: envío gratis y
    #boleto dorado. CUPON_5 (el descuento de siempre) y SIGUE_INTENTANDO
    #("no ganaste") quedan fijos en services.py: no son premios que tenga
    #sentido apagar desde aquí.
    #"""

    class Codigo(models.TextChoices):
        ENVIO_GRATIS = 'ENVIO_GRATIS', 'Envío gratis'
        BOLETO_DORADO = 'BOLETO_DORADO', 'Boleto dorado'

    codigo = models.CharField(max_length=20, choices=Codigo.choices, unique=True)
    peso = models.PositiveSmallIntegerField(
        default=10,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Peso relativo en el sorteo diario (mismo estilo que el % de las campañas).'
    )
    activo = models.BooleanField(
        default=True,
        help_text='Apágalo para sacarlo del sorteo de hoy en adelante, sin perder la configuración.'
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'premio_ruleta_diaria'
        ordering = ['codigo']

    def __str__(self):
        estado = 'activo' if self.activo else 'inactivo'
        return f'{self.get_codigo_display()} ({self.peso}%, {estado})'

class Meta(models.Model):
    #"""
    #Objetivo del negocio para un período, propuesto por el sistema.
    #
    #La idea es que nadie tenga que inventar el número: el motor mira lo
    #que de verdad pasó en los períodos anteriores y propone una meta
    #alcanzable. El admin la acepta, la ajusta o la descarta — pero parte
    #de un dato, no de una corazonada.
    #
    #Una meta descartada no se borra: si se borrara, el motor volvería a
    #proponer lo mismo al día siguiente.
    #"""

    class Tipo(models.TextChoices):
        VENTAS     = 'ventas',     'Ingresos por ventas'
        PRODUCCION = 'produccion', 'Unidades producidas'
        CLIENTES   = 'clientes',   'Clientes nuevos'
        PEDIDOS    = 'pedidos',    'Pedidos entregados'

    class Periodo(models.TextChoices):
        SEMANAL = 'semanal', 'Semanal'
        MENSUAL = 'mensual', 'Mensual'

    class Estado(models.TextChoices):
        PROPUESTA  = 'propuesta',  'Propuesta'
        ACTIVA     = 'activa',     'Activa'
        CUMPLIDA   = 'cumplida',   'Cumplida'
        DESCARTADA = 'descartada', 'Descartada'

    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    periodo = models.CharField(max_length=10, choices=Periodo.choices, default=Periodo.MENSUAL)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PROPUESTA)

    objetivo = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Cuánto hay que alcanzar en el período.'
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    # De dónde salió el número: se guarda para poder explicárselo al
    # admin en vez de mostrarle una cifra caída del cielo.
    base_historica = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Promedio real de los períodos anteriores sobre el que se calculó.'
    )
    periodos_analizados = models.PositiveIntegerField(default=0)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'meta_negocio'
        ordering = ['-fecha_creacion']
        constraints = [
            # Una sola meta viva por tipo y período: si no, el panel
            # mostraría dos objetivos distintos para lo mismo.
            models.UniqueConstraint(
                fields=['tipo', 'fecha_inicio', 'fecha_fin'],
                condition=models.Q(estado__in=['propuesta', 'activa']),
                name='meta_unica_viva_por_tipo_y_periodo',
            ),
        ]

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.objetivo} ({self.get_estado_display()})'


class ConfiguracionEntrega(models.Model):
    #"""
    #Fila única (pk=1) con los tiempos de entrega del negocio.
    #El tiempo de preparación es general (no por pedido): es lo que la
    #cocina tarda en dejar listo cualquier pedido, y el admin lo ajusta
    #desde el panel de Pedidos según cómo venga el día.
    #"""

    minutos_preparacion = models.PositiveIntegerField(
        default=20,
        validators=[MinValueValidator(1), MaxValueValidator(600)],
        help_text='Minutos que tarda la preparación de un pedido antes de salir a ruta.'
    )
    max_pedidos_por_repartidor = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text='Cuántas entregas puede llevar encima un repartidor a la vez. '
                  'Los pedidos que no entran esperan en la cola (estado pendiente).'
    )
    minutos_por_parada = models.PositiveIntegerField(
        default=8,
        validators=[MinValueValidator(1), MaxValueValidator(120)],
        help_text='Lo que tarda el repartidor en cada entrega (estacionar, entregar, '
                  'cobrar). Se suma al tiempo estimado por cada pedido que va antes '
                  'en la ruta.'
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configuracion_entrega'

    def __str__(self):
        return f'Preparación: {self.minutos_preparacion} min'


def obtener_configuracion_entrega():
    #"""Fila única (pk=1). La crea con valores por defecto si no existe."""
    config, _ = ConfiguracionEntrega.objects.get_or_create(
        pk=1, defaults={'minutos_preparacion': 20},
    )
    return config


class SugerenciaSistema(models.Model):
    #"""
    #Ajuste que el sistema propone al admin después de mirar cómo vinieron
    #saliendo los pedidos anteriores.
    #
    #El admin ya no cambia estados a mano (eso lo maneja el motor), pero sí
    #sigue siendo el que decide la configuración del negocio. Cuando los
    #números muestran un patrón — pedidos esperando demasiado en la cola,
    #entregas que siempre tardan más de lo estimado — el sistema deja acá
    #una sugerencia con el valor concreto que recomienda, y el admin la
    #aplica o la descarta de un clic.
    #"""

    class Tipo(models.TextChoices):
        TIEMPO_PREPARACION  = 'tiempo_preparacion',  'Tiempo de preparación'
        MINUTOS_PARADA      = 'minutos_parada',      'Minutos por parada'
        FALTAN_REPARTIDORES = 'faltan_repartidores', 'Faltan repartidores'

    class Estado(models.TextChoices):
        PENDIENTE  = 'pendiente',  'Pendiente'
        APLICADA   = 'aplicada',   'Aplicada'
        DESCARTADA = 'descartada', 'Descartada'

    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PENDIENTE)
    mensaje = models.CharField(max_length=255)
    valor_actual = models.PositiveIntegerField(null=True, blank=True)
    valor_sugerido = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Valor que el sistema recomienda. Nulo en sugerencias que no '
                  'se aplican con un número (ej. "faltan repartidores").'
    )
    muestras = models.PositiveIntegerField(
        default=0, help_text='Cuántos pedidos anteriores se miraron para sacar esta conclusión.'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sugerencia_sistema'
        ordering = ['-fecha_actualizacion']

    def __str__(self):
        return f'{self.get_tipo_display()}: {self.mensaje}'


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
        validators=[MinValueValidator(1), MaxValueValidator(1440)],
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