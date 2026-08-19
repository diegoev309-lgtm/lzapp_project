from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-+95a3_wj16y$#(+rg&)urdt%pbc-dl6vx&le0oz0bw+fy&p8+y'

DEBUG = True

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

# URL base de tu sitio (para back_urls y notificaciones)
SITE_URL = "https://spent-daycare-sludge.ngrok-free.dev"

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'home',
    'usuarios',
    'carrito',
    'dashboard',
    'producto',
    'descuentos',
    'produccion',
    'venta',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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
<<<<<<< HEAD
        'PASSWORD': 'www309edt',
=======
        'PASSWORD': 'admin1234',
>>>>>>> 373893117a999779421412cdc9c6c187f3dddb34
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

LANGUAGE_CODE = 'en-us'
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
