# ==============================================================================
#                                  IMPORTS
# ==============================================================================
import os
from pathlib import Path

import dj_database_url
from decouple import config


# ==============================================================================
#                             CONFIGURAÇÕES BASE
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# URL pública canônica do site (sem barra final).
# Usada para gerar links absolutos nos e-mails (verificação de conta, recuperação de senha).
# Em produção, configure esta variável no painel de Environment Variables do Render.
SITE_URL = config('SITE_URL', default='http://localhost:8000').rstrip('/')

# Configurações de Proxy/HTTPS para deploys em serviços de PaaS (ex: Render)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'https://*.cloudinary.com',
]

# Garante que SITE_URL também está nas origens confiáveis (CSRF)
if SITE_URL and SITE_URL.startswith('https://'):
    CSRF_TRUSTED_ORIGINS.append(SITE_URL)

# Headers de permissão — crítico para autoplay de vídeo funcionar em TVs via Render/Gunicorn.
# O Gunicorn não envia Permissions-Policy por padrão, mas alguns proxies adicionam
# 'autoplay=()' que bloqueia completamente a reprodução de vídeo.
# O middleware abaixo garante que o header correto seja enviado.
PERMISSIONS_POLICY = {
    'autoplay': ['*'],
    'fullscreen': ['*'],
    'picture-in-picture': [],
}

ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ==============================================================================
#                                 APLICAÇÕES
# ==============================================================================
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'axes',
]

THIRD_PARTY_APPS = [
    'anymail',
    'rest_framework',
    'corsheaders',
    'cloudinary',
    'cloudinary_storage',
]

LOCAL_APPS = [
    'painel',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# ==============================================================================
#                                 MIDDLEWARES
# ==============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'corsheaders.middleware.CorsMiddleware',
    'painel.middleware.AutoplayPermissionsMiddleware',  # Headers de autoplay para TVs
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'painel.middleware.TenantMiddleware',
    'axes.middleware.AxesMiddleware',
]


# ==============================================================================
#                                  TEMPLATES
# ==============================================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# ==============================================================================
#                               BANCO DE DADOS
# ==============================================================================
# Fallback automático para SQLite em ambiente de desenvolvimento local.
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600
    )
}


# ==============================================================================
#                               AUTENTICAÇÃO
# ==============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'painel.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Configurações de Sessão e Timeout
SESSION_COOKIE_AGE = 7200  # 2 horas
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Configurações do Django Axes (Proteção contra Força Bruta)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # 1 hora de bloqueio
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
# View para onde o usuário é redirecionado ao ser bloqueado:
AXES_LOCKOUT_URL = '/auth/bloqueado/'

# Configuração de E-mail — django-anymail + Brevo
# Usa a API do Brevo (não SMTP) — ideal para contornar bloqueios e não exige domínio de imediato.
# Configure BREVO_API_KEY no painel de variáveis de ambiente do Render.
# Localmente: deixe em branco para usar o console (imprime no terminal).
_brevo_api_key = config('BREVO_API_KEY', default='')

if _brevo_api_key:
    EMAIL_BACKEND = 'anymail.backends.brevo.EmailBackend'
    ANYMAIL = {
        'BREVO_API_KEY': _brevo_api_key,
    }
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='DisplayDigital <seu_email_brevo@gmail.com>')
else:
    # Fallback seguro: imprime e-mails no terminal quando não há credenciais configuradas
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'no-reply@displaydigital.com'


# ==============================================================================
#                            INTERNACIONALIZAÇÃO
# ==============================================================================
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True


# ==============================================================================
#                              ARQUIVOS E MÍDIA
# ==============================================================================
# Estáticos (CSS, JS, Imagens de layout)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Mídia (Uploads de usuários e arquivos dinâmicos)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Aumentando limites de upload para suportar vídeos pesados
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB

# Ativa o Cloudinary em Produção com o nosso Storage Inteligente
if not DEBUG:
    import cloudinary # Importação necessária para configurar o SDK Global

    DEFAULT_FILE_STORAGE = 'painel.storage.MidiaCloudinaryStorage'
    
    # 1. Configuração para a biblioteca django-cloudinary-storage (Uploads)
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
        'API_KEY': config('CLOUDINARY_API_KEY', default=''),
        'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
        'SECURE': True, # Garante HTTPS
    }

    # 2. CORREÇÃO: Injeção Global para o SDK do Cloudinary (Leitura e Exclusão)
    # Isto resolve a exigência do "CLOUDINARY_URL" usando as suas variáveis separadas
    cloudinary.config(
        cloud_name=config('CLOUDINARY_CLOUD_NAME', default=''),
        api_key=config('CLOUDINARY_API_KEY', default=''),
        api_secret=config('CLOUDINARY_API_SECRET', default=''),
        secure=True
    )


# ==============================================================================
#                                 APIs E CORS
# ==============================================================================
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL', default=True, cast=bool)
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:8000').split(',')

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '5/minute', 
    }
}


# ==============================================================================
#                            SEGURANÇA (PRODUÇÃO)
# ==============================================================================
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# ==============================================================================
#                                 LOGGING
# ==============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'painel': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
