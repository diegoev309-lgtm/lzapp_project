from django.apps import AppConfig


class DescuentosConfig(AppConfig):
    name = 'descuentos'

    def ready(self):
        from . import signals  # noqa: F401 - registra el receptor de user_logged_in (migrar tirada anónima)
    