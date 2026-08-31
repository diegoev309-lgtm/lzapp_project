from django.db import migrations

# Mismos pesos que tenía TABLA_PREMIOS_RULETA_DIARIA hardcodeada en
# descuentos/services.py, para que activar este control desde el
# dashboard no cambie las probabilidades existentes hasta que alguien
# las edite a propósito.
PESOS_INICIALES = {
    'ENVIO_GRATIS': 12,
    'BOLETO_DORADO': 8,
}


def crear_premios(apps, schema_editor):
    PremioRuletaDiaria = apps.get_model('dashboard', 'PremioRuletaDiaria')
    for codigo, peso in PESOS_INICIALES.items():
        PremioRuletaDiaria.objects.get_or_create(
            codigo=codigo,
            defaults={'peso': peso, 'activo': True},
        )


def eliminar_premios(apps, schema_editor):
    PremioRuletaDiaria = apps.get_model('dashboard', 'PremioRuletaDiaria')
    PremioRuletaDiaria.objects.filter(codigo__in=PESOS_INICIALES.keys()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0015_premioruletadiaria'),
    ]

    operations = [
        migrations.RunPython(crear_premios, eliminar_premios),
    ]
