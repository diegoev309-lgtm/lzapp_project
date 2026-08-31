"""
Borra las filas de SesionActiva cuya sesión de Django ya no existe (expiró
y fue barrida, o el proceso terminó sin pasar por logout()). El cruce que
usa panel_seguridad ya "oculta" estas filas huérfanas de la vista (solo
lista sesiones con expire_date vigente), pero nunca las borra por sí solo
-- este comando es el que efectivamente libera esas filas de la base.

Pensado para correr junto (después) de `manage.py clearsessions`.

Uso:
    python manage.py limpiar_sesiones_inactivas

Ejemplo de entrada en crontab (todos los días a las 3:10 AM, después de
clearsessions a las 3:00 AM):
    0 3 * * * cd /ruta/al/proyecto && /ruta/al/venv/bin/python manage.py clearsessions
    10 3 * * * cd /ruta/al/proyecto && /ruta/al/venv/bin/python manage.py limpiar_sesiones_inactivas >> /var/log/seguridad.log 2>&1
"""

from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand

from seguridad.models import SesionActiva


class Command(BaseCommand):
    help = 'Borra las filas de SesionActiva cuya sesión de Django ya no existe.'

    def handle(self, *args, **options):
        claves_vigentes = Session.objects.values_list('session_key', flat=True)
        huerfanas, _ = SesionActiva.objects.exclude(session_key__in=claves_vigentes).delete()

        self.stdout.write(self.style.SUCCESS(
            f'Se eliminaron {huerfanas} fila(s) de SesionActiva huérfanas.'
        ))
