"""Produção. Ver ARCHITECTURE.md §13 — checklist de segurança obrigatório."""

from .base import *  # noqa: F403
from .base import env

DEBUG = False

# `env.list(...)` sem `default` levanta `ImproperlyConfigured` e derruba o
# processo se a variável não existir — mesmo problema que já resolvemos pro
# SECRET_KEY. Aqui o fallback seguro é lista vazia (Django recusa toda
# requisição, nunca aceita qualquer host por omissão) MAIS o domínio público
# que o Railway injeta sozinho (`RAILWAY_PUBLIC_DOMAIN`) — assim o primeiro
# deploy já funciona no domínio que o próprio Railway gerou, sem precisar
# configurar `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` manualmente antes de saber
# qual vai ser esse domínio.
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

RAILWAY_PUBLIC_DOMAIN = env("RAILWAY_PUBLIC_DOMAIN", default="")
if RAILWAY_PUBLIC_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)
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
