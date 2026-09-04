"""Configurações comuns a todos os ambientes. Nada de segredo com valor real
aqui dentro — tudo vem de variável de ambiente (ver ARCHITECTURE.md §13)."""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = False

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "apps.core",
    "apps.users",
    "apps.audit",
    "apps.customers",
    "apps.documents",
    "apps.quotations",
    "apps.projects",
    "apps.finance",
    "apps.mercadopago",
    "apps.notifications",
    "apps.whatsapp",
    "apps.dashboard",
    "apps.reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Dev: filesystem local. Produção: trocar por storage externo (S3-compatível)
# via STORAGES["default"] — sem tocar em apps/documents/models.py (ARCHITECTURE.md §14).
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # Não é o `JWTAuthentication` puro do simplejwt — ver
        # `apps/users/authentication.py` (Fase 10, ARCHITECTURE.md §13):
        # aplica a trava de 2FA obrigatório pra qualquer view, sem que cada
        # ViewSet precise saber que essa trava existe.
        "apps.users.authentication.TwoFactorAwareJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    # Rate limiting (§13) — só nos endpoints que declaram `throttle_scope`
    # (login e o webhook do Mercado Pago); o resto da API não é limitado por
    # aqui, pra não pré-otimizar um limite genérico sem necessidade real.
    "DEFAULT_THROTTLE_CLASSES": ("rest_framework.throttling.ScopedRateThrottle",),
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/min",
        "mercadopago-webhook": "60/min",
    },
}

SIMPLE_JWT = {
    # Curto: perfil administrativo/financeiro não deve segurar um access token
    # válido por horas. O refresh é quem sustenta a sessão.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    # Um refresh token trocado (rotacionado) não pode ser reusado — sem isto,
    # um refresh token vazado continua válido até expirar mesmo depois de já
    # ter sido usado uma vez por quem tinha direito (§13, segurança de sessão).
    "BLACKLIST_AFTER_ROTATION": True,
}

# Mercado Pago (ARCHITECTURE.md §10) — nenhuma chamada HTTP ao provedor fora
# de `apps/mercadopago/`. Sem token configurado, `finance.services.issue_charge`
# recusa com um erro de domínio claro, em vez de qualquer app tentar montar a
# URL/credencial na mão. `MERCADOPAGO_BASE_URL` existe pra poder apontar pra
# um stub local em teste/smoke, sem precisar de credencial real.
MERCADOPAGO_ACCESS_TOKEN = env("MERCADOPAGO_ACCESS_TOKEN", default="")
MERCADOPAGO_BASE_URL = env("MERCADOPAGO_BASE_URL", default="https://api.mercadopago.com")
# Opcional: valida a assinatura `x-signature` do webhook quando configurado.
# A proteção que não é opcional é a verificação via `client.get_payment`
# logo abaixo — o webhook nunca dá baixa financeira só porque a assinatura bateu.
MERCADOPAGO_WEBHOOK_SECRET = env("MERCADOPAGO_WEBHOOK_SECRET", default="")

# Evolution API (ARCHITECTURE.md §6.9, §11). Sem configurar, `whatsapp.client`
# recusa com um erro claro — `notifications.dispatch_pending` marca a
# notificação como falhada e tenta de novo depois, nunca derruba quem criou o
# aviso (§59).
EVOLUTION_API_BASE_URL = env("EVOLUTION_API_BASE_URL", default="")
EVOLUTION_API_KEY = env("EVOLUTION_API_KEY", default="")
EVOLUTION_API_INSTANCE = env("EVOLUTION_API_INSTANCE", default="")

# Logging estruturado — texto simples com timestamp/nível/módulo em produção
# também, não só em dev. JSON entra quando um agregador de logs precisar dele
# (ARCHITECTURE.md §54 da spec técnica não exige um formato específico ainda).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
