from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from apps.core.views import health, spa_index
from apps.mercadopago.webhooks import MercadoPagoWebhookView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/v1/", include("apps.users.api.urls")),
    path("api/v1/", include("apps.customers.api.urls")),
    path("api/v1/", include("apps.documents.api.urls")),
    path("api/v1/", include("apps.quotations.api.urls")),
    path("api/v1/", include("apps.projects.api.urls")),
    path("api/v1/finance/", include("apps.finance.api.urls")),
    path("api/v1/support/", include("apps.support.api.urls")),
    path("api/v1/audit/", include("apps.audit.api.urls")),
    path("api/v1/settings/", include("apps.core.api.urls")),
    path("api/v1/dashboard/", include("apps.dashboard.api.urls")),
    path("api/v1/reports/", include("apps.reports.api.urls")),
    # Fora do /api/v1/ de propósito — webhook de provedor externo (ARCHITECTURE.md §12).
    path("api/webhooks/mercadopago/", MercadoPagoWebhookView.as_view(), name="mercadopago-webhook"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Sempre por último: qualquer rota que não seja admin/api/health cai no SPA
# do React (deploy de serviço único — Dockerfile builda o frontend e o
# Django serve o `dist/`). Os assets (`/assets/...`) são servidos pelo
# WhiteNoiseMiddleware via `WHITENOISE_ROOT`, não por esta rota.
urlpatterns += [re_path(r"^.*$", spa_index)]
