from dotenv import load_dotenv
load_dotenv()
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-+95a3_wj16y$#(+rg&)urdt%pbc-dl6vx&le0oz0bw+fy&p8+y'

DEBUG = True

# settings.py
GOOGLE_MAPS_API_KEY = ''
USAR_DISTANCE_MATRIX = False   # cambiar a True cuando GOOGLE_MAPS_API_KEY esté activo

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Endurecimiento de transporte/cookies -- atado a "not DEBUG" para no romper
# las pruebas actuales por http en la red local (ver comentario de
# runserver 0.0.0.0:8000 más abajo); se activa solo cuando el proyecto
# corra en producción con DEBUG=False. Protege datos sensibles en tránsito
# (ubicación del cliente, sesión) contra sniffing/robo de cookie.
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

ALLOWED_HOSTS = ['*']
# para la misma red
#Usar el comando python manage.py runserver 0.0.0.0:8000 para ejecutar lo en otra pc y http://192.168.1.51:8000/

# ngrok http 8000
CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.app',
    'https://*.ngrok-free.dev',
]

# para hacer la simulacion de los descuentos:
#python manage.py simular_flujo_descuentos   para correr
#python manage.py simular_flujo_descuentos --limpiar   para eliminar todos los usuarios creados para la simulacion

# settings.py
MERCADOPAGO_ACCESS_TOKEN = "APP_USR-3569434423018606-072916-47fd605aeda608e3647b1d515e5f680b-3575141051"
MERCADOPAGO_PUBLIC_KEY = "APP_USR-e9497343-694d-4adc-83e6-2403bcab07c0"

# URL base de tu sitio (para back_urls y notificaciones).
# Dominio reservado de ngrok (no cambia entre reinicios del túnel, a
# diferencia de una URL aleatoria de "ngrok http 8000" sin --url).
SITE_URL = "https://spent-daycare-sludge.ngrok-free.dev"

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',
    'home',
    'usuarios',
    'carrito',
    'dashboard',
    'producto',
    'pedido',
    'descuentos',
    'produccion',
    'venta',
    'notificacion',
    'seguridad',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'allauth.account.middleware.AccountMiddleware', 
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Al final: necesita request.user (AuthenticationMiddleware) y
    # request._messages (MessageMiddleware) ya listos.
    'seguridad.middleware.SeguridadSesionMiddleware',
]

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],

        'AUTH_PARAMS': {
            'access_type': 'online',
        },

        # Permitir que Google autentique
        # una cuenta local que tenga el mismo email.
        'EMAIL_AUTHENTICATION': True,

        # Vincular automáticamente la cuenta Google
        # con la cuenta local encontrada por email.
        'EMAIL_AUTHENTICATION_AUTO_CONNECT': True,
    }
}

SOCIALACCOUNT_AUTO_SIGNUP = True

SOCIALACCOUNT_LOGIN_ON_GET = True

ROOT_URLCONF = 'lzapp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'carrito.context_processor.totalizar_carro',
                "carrito.context_processor.mercadopago_public_key",
                "notificacion.context_processor.notificaciones_admin",
                "seguridad.context_processors.configuracion_seguridad",
            ],
        },
    },
]

WSGI_APPLICATION = 'lzapp.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'db_lzapp',
        'USER': 'root',
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '3306',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ── Archivos estáticos ──────────────────────────────────────────────
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'home' / 'static',  # <-- ESTE ES EL CAMBIO
]

# ── Archivos de media ───────────────────────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ── Email ───────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST_USER = "lacteoslzaap@gmail.com"
EMAIL_HOST_PASSWORD = "eooiutauqloeajyn"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = '/client'
# Sin esto, cualquier @login_required sin login_url explícito caía en el
# /accounts/login/ de allauth en vez del login real del proyecto.
LOGIN_URL = 'login'