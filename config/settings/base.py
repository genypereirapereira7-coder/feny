"""Configurações comuns a todos os ambientes. Nada de segredo com valor real
aqui dentro — tudo vem de variável de ambiente (ver ARCHITECTURE.md §13)."""

import os
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# `os.getenv` com fallback em vez de `env("SECRET_KEY")` — este último levanta
# `ImproperlyConfigured` e derruba o processo se a variável não existir, o
# que já quebrou o primeiro deploy antes de qualquer chance de configurar a
# variável de verdade no painel do provedor.
#
# O fallback é de desenvolvimento, e é **público**: está escrito aqui, num
# repositório aberto. Quem o conhece assina sessão do Django e token JWT
# (`SIMPLE_JWT` usa a SECRET_KEY pra assinar) — ou seja, entra como qualquer
# usuário sem saber senha nenhuma. Por isso ele não pode simplesmente valer
# em produção.
_SECRET_KEY_DEV = "django-insecure-fallback-temporario-troque-em-producao"

SECRET_KEY = os.getenv("SECRET_KEY", _SECRET_KEY_DEV)

# Estamos num ambiente de verdade? Duas pistas independentes: o módulo de
# settings escolhido e as variáveis que o próprio provedor injeta.
_MARCAS_DE_HOSPEDAGEM = ("RAILWAY_ENVIRONMENT", "RAILWAY_PROJECT_ID", "RENDER", "FLY_APP_NAME")
_SETTINGS_MODULE = os.getenv("DJANGO_SETTINGS_MODULE", "")

_EM_PRODUCAO = _SETTINGS_MODULE.endswith(("production", "staging")) or any(
    os.environ.get(marca) for marca in _MARCAS_DE_HOSPEDAGEM
)

if _EM_PRODUCAO and SECRET_KEY == _SECRET_KEY_DEV:
    # **Não derruba o arranque.** Foi exatamente o `ImproperlyConfigured` que
    # quebrou o primeiro deploy, e trocar um erro de partida por outro não
    # resolve nada. Uma chave sorteada agora assina tão bem quanto uma do
    # painel; o que se perde é permanência — a cada reinício ela é outra, e
    # quem estava logado no painel digita a senha de novo.
    import logging as _logging
    import secrets as _secrets

    SECRET_KEY = _secrets.token_urlsafe(50)
    _logging.getLogger(__name__).error(
        "\n"
        "  ============================================================\n"
        "   SECRET_KEY NAO ESTA DEFINIDA\n"
        "  ============================================================\n"
        "   O padrao do codigo esta publicado no repositorio: com ele,\n"
        "   qualquer pessoa assina sessao e token JWT deste sistema.\n"
        "\n"
        "   Subi com uma chave sorteada agora, so pra esta execucao.\n"
        "   Defina a variavel no painel:\n"
        "       python -c \"import secrets; print(secrets.token_urlsafe(50))\"\n"
        "  ============================================================\n"
    )
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
    "corsheaders",
    "apps.core",
    "apps.users",
    "apps.audit",
    "apps.customers",
    "apps.leads",
    "apps.documents",
    "apps.quotations",
    "apps.projects",
    "apps.finance",
    "apps.support",
    "apps.mercadopago",
    "apps.notifications",
    "apps.whatsapp",
    "apps.dashboard",
    "apps.reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serve estáticos (admin) direto do processo Django — sem storage externo
    # nem servidor à parte, suficiente pra uma API interna (Railway/Render não
    # dão hospedagem de estático de graça pro `collectstatic` como o Nginx
    # de um deploy tradicional daria).
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # Precisa vir antes do CommonMiddleware (exigência do django-cors-headers).
    "corsheaders.middleware.CorsMiddleware",
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

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Hash no nome do arquivo + compressão — cache longo no navegador sem
    # risco de servir versão velha depois de um deploy (whitenoise cuida do
    # `Cache-Control` sozinho quando o storage é este).
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# `frontend_dist/` só existe dentro da imagem Docker (o Dockerfile builda o
# React no primeiro estágio e copia o `dist/` pra cá — ver Dockerfile). Sem a
# checagem `is_dir()`, rodar localmente sem ter buildado o frontend derrubaria
# o whitenoise na inicialização. Serve os arquivos na raiz do domínio (não sob
# `/static/`) porque é onde o `index.html` do Vite espera achar seus assets.
FRONTEND_DIST_DIR = BASE_DIR / "frontend_dist"
if FRONTEND_DIST_DIR.is_dir():
    WHITENOISE_ROOT = FRONTEND_DIST_DIR

# Dev: filesystem local. Produção: trocar por storage externo (S3-compatível)
# via STORAGES["default"] — sem tocar em apps/documents/models.py (ARCHITECTURE.md §14).
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Frontend (React/Vite) roda em origem separada — CORS_ALLOWED_ORIGINS tem um
# default de dev (a porta padrão do `npm run dev`) pra funcionar sem precisar
# editar `.env`; staging/production sobrescrevem via variável de ambiente.
# 5173 é o Vite (painel em desenvolvimento); 4200 é o servidor estático da
# landing. Em produção os dois são servidos pelo próprio Django, mesma
# origem, e esta lista não é usada.
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS", default=["http://localhost:5173", "http://localhost:4200"]
)
CORS_ALLOW_CREDENTIALS = True

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
    # (login, o webhook do Mercado Pago e o formulário público do site); o
    # resto da API não é limitado por aqui, pra não pré-otimizar um limite
    # genérico sem necessidade real.
    "DEFAULT_THROTTLE_CLASSES": ("rest_framework.throttling.ScopedRateThrottle",),
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/min",
        "mercadopago-webhook": "60/min",
        # Formulário de contato do site institucional — é a única porta da
        # API aberta sem login, então precisa de teto por IP. 5/min deixa
        # passar quem errou um campo e reenviou, e corta script de spam.
        "lead-public": "5/min",
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

# Agente de IA do WhatsApp (Typebot). Segredo combinado, conferido no cabeçalho
# `X-Webhook-Token` por `apps.leads.views.webhook_whatsapp_ia`. Sem ele o
# webhook recusa tudo, de propósito: é uma porta aberta pra internet que
# escreve no banco, e deploy sem a variável fica sem integração (problema
# visível) em vez de ficar sem tranca (problema invisível).
WHATSAPP_IA_WEBHOOK_TOKEN = env("WHATSAPP_IA_WEBHOOK_TOKEN", default="")

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
