from django.apps import AppConfig


class SeguridadConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'seguridad'

    def ready(self):
        from . import signals  # noqa: F401 - registra los receptores de user_logged_in/out
