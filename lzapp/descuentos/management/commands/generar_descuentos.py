"""
Comando programado para ejecutar las campañas de descuento pendientes.

Pensado para correr vía cron o Celery beat. La periodicidad real (semanal/mensual)
la decide cada CampanaDescuento con su campo `frecuencia`; este comando se puede
programar para correr, por ejemplo, todos los días a una hora fija, y es
`ejecutar_campanas_pendientes()` quien filtra cuáles campañas realmente les
corresponde ejecutarse ese día (evita duplicar lógica de calendario en dos lugares).

Uso:
    python manage.py generar_descuentos
    python manage.py generar_descuentos --dry-run
    python manage.py generar_descuentos --campana-id 3

Ejemplo de entrada en crontab (todos los días a las 3:00 AM):
    0 3 * * * cd /ruta/al/proyecto && /ruta/al/venv/bin/python manage.py generar_descuentos >> /var/log/descuentos.log 2>&1
"""

import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from dashboard.models import CampanaDescuento
from descuentos.services import (
    ejecutar_campana,
    ejecutar_campanas_pendientes,
    previsualizar_campana,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Ejecuta las campañas de descuento activas que les corresponda correr "
        "hoy según su frecuencia (semanal/mensual). Sin argumentos, procesa "
        "todas las campañas pendientes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--campana-id",
            type=int,
            default=None,
            help="Si se indica, ejecuta solo esa campaña (ignorando si le tocaba o no hoy).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo previsualiza (cuenta clientes/stock) sin asignar descuentos ni tocar la base de datos.",
        )

    def handle(self, *args, **options):
        inicio = timezone.now()
        campana_id = options.get("campana_id")
        dry_run = options.get("dry_run")

        self.stdout.write(
            self.style.NOTICE(
                f"[{inicio:%Y-%m-%d %H:%M:%S}] Iniciando generación de descuentos "
                f"(dry-run={dry_run})"
            )
        )

        # --- Modo: una sola campaña puntual (útil para pruebas manuales) ---
        if campana_id is not None:
            try:
                campana = CampanaDescuento.objects.get(pk=campana_id)
            except CampanaDescuento.DoesNotExist:
                raise CommandError(f"No existe una CampanaDescuento con id={campana_id}")

            if not campana.activo:
                self.stdout.write(
                    self.style.WARNING(
                        f"La campaña '{campana}' (id={campana_id}) está inactiva. "
                        "No se ejecuta (usa el panel para activarla si quieres forzarla)."
                    )
                )
                return

            if dry_run:
                self._mostrar_previsualizacion(campana)
                return

            resultado = ejecutar_campana(campana)
            self._reportar_resultado(campana, resultado)
            return

        # --- Modo: todas las campañas pendientes según su frecuencia ---
        if dry_run:
            campanas_activas = CampanaDescuento.objects.filter(activo=True)
            if not campanas_activas.exists():
                self.stdout.write(self.style.WARNING("No hay campañas activas."))
                return
            for campana in campanas_activas:
                self._mostrar_previsualizacion(campana)
            return

        try:
            resultados = ejecutar_campanas_pendientes()
        except Exception as exc:
            # No dejamos morir el comando silenciosamente: esto es lo que ve el cron log.
            logger.exception("Error ejecutando campañas de descuento pendientes")
            raise CommandError(f"Falló la ejecución de campañas pendientes: {exc}")

        if not resultados:
            self.stdout.write(self.style.WARNING("No había campañas pendientes hoy."))
            return

        for campana, resultado in resultados:
            self._reportar_resultado(campana, resultado)

        fin = timezone.now()
        self.stdout.write(
            self.style.SUCCESS(
                f"[{fin:%Y-%m-%d %H:%M:%S}] Generación de descuentos completada "
                f"en {(fin - inicio).total_seconds():.1f}s."
            )
        )

    # ------------------------------------------------------------------ #
    # Helpers de salida en consola/log
    # ------------------------------------------------------------------ #

    def _mostrar_previsualizacion(self, campana):
        """Imprime el mismo desglose que ve el usuario en el modal del panel,
        pero en texto plano, sin asignar nada."""
        preview = previsualizar_campana(campana)
        self.stdout.write(
            self.style.NOTICE(
                f"\n[DRY-RUN] Campaña '{campana}' (id={campana.pk})\n"
                f"  Producto: {campana.producto}\n"
                f"  Clientes totales activos: {preview.get('total_clientes_activos')}\n"
                f"  Tope por porcentaje: {preview.get('tope_por_porcentaje')}\n"
                f"  Stock disponible para ofertar: {preview.get('stock_disponible')}\n"
                f"  Clientes elegibles (sin compra reciente): {preview.get('total_elegibles')}\n"
                f"  Ganadores finales (mínimo de los 3 topes): {preview.get('ganadores_finales')}\n"
            )
        )

    def _reportar_resultado(self, campana, resultado):
        """Reporta el resultado real de ejecutar_campana()/ejecutar_campanas_pendientes().

        Se asume que `resultado` es un dict con al menos `descuentos_creados`;
        si tu implementación de services.py devuelve otra forma, ajusta aquí
        (es el único punto que depende de ese contrato).
        """
        creados = resultado.get("descuentos_creados", resultado) if isinstance(resultado, dict) else resultado
        self.stdout.write(
            self.style.SUCCESS(
                f"✔ Campaña '{campana}' (id={campana.pk}) ejecutada: "
                f"{creados} descuentos asignados."
            )
        )