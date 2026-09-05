"""Produção. Ver ARCHITECTURE.md §13 — checklist de segurança obrigatório."""

from .base import *  # noqa: F403
from .base import env

DEBUG = False

# Aceita qualquer Host (a pedido) — Django não faz mais nenhuma validação do
# cabeçalho Host nesta instância. Isto desliga uma proteção de verdade contra
# ataques de Host header (cache/password-reset poisoning); manter restrito ao
# domínio real (a lógica de `RAILWAY_PUBLIC_DOMAIN` abaixo fazia isso sozinho)
# é o que ARCHITECTURE.md §13 recomenda. Reverter é só trocar a linha de volta
# pra `env.list("ALLOWED_HOSTS", default=[])`.
ALLOWED_HOSTS = ["*"]

# `env.list(...)` sem `default` levanta `ImproperlyConfigured` e derruba o
# processo se a variável não existir — mesmo problema que já resolvemos pro
# SECRET_KEY. CSRF_TRUSTED_ORIGINS não aceita "*" (Django exige origem com
# esquema), então continua vindo de env + o domínio que o Railway injeta
# sozinho (`RAILWAY_PUBLIC_DOMAIN`).
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

RAILWAY_PUBLIC_DOMAIN = env("RAILWAY_PUBLIC_DOMAIN", default="")
if RAILWAY_PUBLIC_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RAILWAY_PUBLIC_DOMAIN}")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Atrás de um proxy reverso (Render, Nginx etc.) que já termina TLS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Observabilidade (§18, Fase 10) — opcional: sem DSN configurado, roda sem
# rastreamento de erro nenhum, sem quebrar nada.
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        send_default_pii=False,  # nunca manda dado pessoal de request pro Sentry (§13)
        traces_sample_rate=0.1,
    )
