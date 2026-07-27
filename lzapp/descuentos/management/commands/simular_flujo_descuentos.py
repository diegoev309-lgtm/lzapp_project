"""
Comando de simulación del módulo de descuentos.

Objetivo: crear clientes y ventas FICTICIAS (que no tocan datos reales)
para poder correr previsualizar_campana()/ejecutar_campana() sobre datos
controlados y validar todo el flujo end-to-end antes de construir pagos:

    elegibilidad -> stock -> topes -> asignación -> aparición en el home

Uso típico:

    # Simula sobre TODAS las campañas activas, creando 20 clientes de
    # prueba por campaña (40% de ellos "ya compraron" el producto y por
    # tanto NO deben calificar), solo mostrando qué pasaría (no crea nada):
    python manage.py simular_flujo_descuentos --dry-run

    # Simula de verdad (crea DescuentoAsignado) sobre una campaña puntual:
    python manage.py simular_flujo_descuentos --campana-id 3

    # Limpia todo lo que este comando haya creado antes:
    python manage.py simular_flujo_descuentos --limpiar
"""

import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from dashboard.models import CampanaDescuento, DetalleVenta, Perfil, Venta
from descuentos.services import ejecutar_campana, previsualizar_campana

# Prefijo fijo para poder identificar (y luego borrar) SOLO lo que
# generó este comando, sin arriesgar tocar clientes reales.
PREFIJO_PRUEBA = 'prueba_desc_'


class Command(BaseCommand):
    help = (
        'Crea clientes y ventas ficticias (identificables por un prefijo) '
        'para simular el flujo completo de una o varias campañas de '
        'descuento, sin afectar clientes ni ventas reales.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--campana-id', type=int, default=None,
            help='Simular solo esta campaña puntual. Si se omite, se simulan todas las campañas activas.'
        )
        parser.add_argument(
            '--clientes', type=int, default=20,
            help='Cantidad de clientes ficticios a crear por campaña (default: 20).'
        )
        parser.add_argument(
            '--porcentaje-compradores', type=float, default=40.0,
            help='Porcentaje (0-100) de esos clientes que se marcan como que YA '
                 'compraron el producto recientemente, para que NO califiquen '
                 '(sirve para probar que la exclusión funciona). Default: 40.'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Solo previsualiza (previsualizar_campana), no crea ningún DescuentoAsignado.'
        )
        parser.add_argument(
            '--limpiar', action='store_true',
            help='Elimina TODOS los clientes/ventas/premios de prueba generados por este '
                 'comando anteriormente, y termina (no simula nada más).'
        )

    def handle(self, *args, **options):
        if options['limpiar']:
            self._limpiar()
            return

        campanas = self._obtener_campanas(options['campana_id'])
        if not campanas:
            self.stdout.write(self.style.WARNING('No hay campañas activas para simular.'))
            return

        for campana in campanas:
            self.stdout.write(self.style.HTTP_INFO(f'\n=== Campaña: {campana.nombre} ==='))

            if not campana.productos.exists():
                self.stdout.write(self.style.WARNING('  (sin productos asociados, se omite)'))
                continue

            self._crear_clientes_y_ventas(
                campana=campana,
                cantidad_clientes=options['clientes'],
                porcentaje_compradores=options['porcentaje_compradores'],
            )

            if options['dry_run']:
                resultado = previsualizar_campana(campana)
                self._mostrar_previsualizacion(resultado)
            else:
                resultado = ejecutar_campana(campana)
                self._mostrar_resultado_ejecucion(resultado)
                # Solo tiene sentido mostrar ganadores/perdedores reales
                # cuando sí se crearon DescuentoAsignado (no en --dry-run).
                self._mostrar_resumen_pruebas(campana)

        self.stdout.write(self.style.SUCCESS('\nSimulación terminada.'))

    # ------------------------------------------------------------------
    # Creación de datos de prueba
    # ------------------------------------------------------------------

    def _obtener_campanas(self, campana_id):
        if campana_id:
            try:
                return [CampanaDescuento.objects.get(pk=campana_id)]
            except CampanaDescuento.DoesNotExist:
                raise CommandError(f'No existe una campaña con id {campana_id}.')
        return list(CampanaDescuento.objects.filter(activo=True))

    @transaction.atomic
    def _crear_clientes_y_ventas(self, campana, cantidad_clientes, porcentaje_compradores):
        """
        Crea `cantidad_clientes` usuarios de prueba nuevos (con un sufijo
        aleatorio para no chocar con corridas previas) y, para cada
        producto de la campaña, hace que un % de ellos "ya hayan comprado"
        ese producto dentro de la ventana de dias_sin_compra (para que la
        exclusión de obtener_ids_clientes_elegibles() tenga algo real que
        excluir). El resto queda elegible.
        """
        sufijo_corrida = timezone.now().strftime('%H%M%S')
        usuarios_creados = []

        for i in range(cantidad_clientes):
            username = f'{PREFIJO_PRUEBA}{campana.id}_{sufijo_corrida}_{i}'
            usuario = User.objects.create_user(
                username=username,
                email=f'{username}@prueba.local',
                password='no-usable-123',  # no se usa para login real, solo para pasar validaciones
            )
            # Perfil es OneToOne con User y no lo crea create_user() solo;
            # sin esto, cualquier vista/template que espere
            # request.user.perfil revienta con RelatedObjectDoesNotExist.
            Perfil.objects.create(usuario=usuario, telefono=f'300000{i:04d}')
            usuarios_creados.append(usuario)

        cantidad_compradores = int(cantidad_clientes * (porcentaje_compradores / 100))
        compradores = random.sample(usuarios_creados, min(cantidad_compradores, len(usuarios_creados)))

        # Fecha DENTRO de la ventana de dias_sin_compra: deben quedar excluidos.
        fecha_compra_reciente = timezone.now() - timedelta(days=max(campana.dias_sin_compra // 2, 1))

        for producto in campana.productos.all():
            for comprador in compradores:
                venta = Venta.objects.create(usuario=comprador, total=producto.precio)
                # Ajustamos la fecha manualmente porque `fecha` es auto_now_add.
                Venta.objects.filter(pk=venta.pk).update(fecha=fecha_compra_reciente)
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=1,
                    precio_unitario=producto.precio,
                )

        self.stdout.write(
            f'  Creados {len(usuarios_creados)} clientes de prueba '
            f'({len(compradores)} marcados como "ya compraron recientemente", '
            f'{len(usuarios_creados) - len(compradores)} elegibles).'
        )

    # ------------------------------------------------------------------
    # Reportes en consola
    # ------------------------------------------------------------------

    def _mostrar_previsualizacion(self, resultado):
        if 'error' in resultado:
            self.stdout.write(self.style.ERROR(f'  {resultado["error"]}'))
            return
        for item in resultado.get('detalle', []):
            self.stdout.write(
                f'  Producto: {item["producto"]}\n'
                f'    Clientes activos totales: {item["total_clientes_activos"]}\n'
                f'    Tope por %: {item["limite_por_porcentaje"]}\n'
                f'    Stock ofertable: {item["stock_ofertable"]}\n'
                f'    Elegibles encontrados: {item["clientes_elegibles_encontrados"]}\n'
                f'    --> Recibirían el premio: {item["clientes_que_recibiran_el_premio"]}'
            )

    def _mostrar_resultado_ejecucion(self, resultado):
        if 'error' in resultado:
            self.stdout.write(self.style.ERROR(f'  {resultado["error"]}'))
            return
        for item in resultado.get('productos', []):
            ganadores = item.get('ganadores_creados', 0)
            self.stdout.write(
                f'  Producto: {item["producto"]}\n'
                f'    Clientes activos totales: {item["total_clientes_activos"]}\n'
                f'    Tope por % ({item.get("limite_por_porcentaje")}) / '
                f'Stock ofertable: {item["stock_ofertable"]}\n'
                f'    Elegibles encontrados: {item["clientes_elegibles_encontrados"]}\n'
                f'    Ganadores creados: {ganadores}'
                + (f' (precio final: {item.get("precio_final")})' if ganadores else '')
            )
            if item.get('motivo_si_cero'):
                self.stdout.write(self.style.WARNING(f'    Motivo de 0 ganadores: {item["motivo_si_cero"]}'))

    def _mostrar_resumen_pruebas(self, campana):
        """
        Muestra, para ESTA campaña, qué clientes de prueba ganaron premio
        (con su código de descuento) y una muestra de los que NO ganaron,
        para poder iniciar sesión con ambos y comparar el carrusel del
        home lado a lado sin tener que ir al admin o al shell.
        """
        from dashboard.models import DescuentoAsignado  # import local: evita ciclos con dashboard

        ganadores = DescuentoAsignado.objects.filter(
            campana=campana,
            usuario__username__startswith=PREFIJO_PRUEBA,
        ).select_related('usuario', 'producto')

        ids_ganadores = ganadores.values_list('usuario_id', flat=True)
        perdedores = User.objects.filter(
            username__startswith=PREFIJO_PRUEBA,
        ).exclude(id__in=ids_ganadores)

        self.stdout.write(self.style.HTTP_INFO('\n  --- Resumen para probar el carrusel ---'))
        self.stdout.write('  Contraseña de todos los usuarios de prueba: no-usable-123\n')

        if ganadores:
            self.stdout.write(self.style.SUCCESS('  Clientes GANADORES (deberían ver la oferta en el home):'))
            for d in ganadores:
                self.stdout.write(f'    - {d.usuario.username}  ({d.producto.nombre}, código {d.codigo})')
        else:
            self.stdout.write(self.style.WARNING('  No hubo ganadores para esta campaña en esta corrida.'))

        muestra_perdedores = list(perdedores[:5])
        if muestra_perdedores:
            self.stdout.write(self.style.WARNING('  Clientes SIN premio (no deberían ver la oferta), muestra:'))
            for u in muestra_perdedores:
                self.stdout.write(f'    - {u.username}')

    # ------------------------------------------------------------------
    # Limpieza
    # ------------------------------------------------------------------

    def _limpiar(self):
        """
        Borra usuarios de prueba (y por CASCADE sus Venta/DetalleVenta y
        sus DescuentoAsignado, ya que ambos modelos apuntan a User con
        on_delete=CASCADE). No toca ningún cliente real.
        """
        usuarios_prueba = User.objects.filter(username__startswith=PREFIJO_PRUEBA)
        total = usuarios_prueba.count()
        usuarios_prueba.delete()
        self.stdout.write(self.style.SUCCESS(f'Eliminados {total} cliente(s) de prueba y todos sus datos asociados.'))