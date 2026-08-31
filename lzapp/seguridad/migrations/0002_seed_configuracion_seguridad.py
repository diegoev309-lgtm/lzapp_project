from django.db import migrations


def crear_configuracion(apps, schema_editor):
    ConfiguracionSeguridad = apps.get_model('seguridad', 'ConfiguracionSeguridad')
    ConfiguracionSeguridad.objects.get_or_create(
        pk=1,
        defaults={'deteccion_inactividad_activa': True, 'minutos_inactividad': 15},
    )


def eliminar_configuracion(apps, schema_editor):
    ConfiguracionSeguridad = apps.get_model('seguridad', 'ConfiguracionSeguridad')
    ConfiguracionSeguridad.objects.filter(pk=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('seguridad', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(crear_configuracion, eliminar_configuracion),
    ]
