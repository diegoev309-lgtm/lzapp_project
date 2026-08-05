from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


# =========================================================
# JUEGO DIARIO ("Ruleta del día") — PARTE 2
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
