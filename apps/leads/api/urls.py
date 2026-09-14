from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.leads.api.views import LeadViewSet, PublicLeadCreateView

router = DefaultRouter()
router.register("leads", LeadViewSet, basename="lead")

urlpatterns = [
    # Fora do router de propósito: é o único endpoint público da plataforma
    # (site institucional → formulário de contato). Nome e caminho distintos
    # deixam isso óbvio pra quem lê `config/urls.py` e pra qualquer regra de
    # WAF/proxy que precise tratar essa rota diferente do resto da API.
    path("public/contact/", PublicLeadCreateView.as_view(), name="public-contact"),
    path("", include(router.urls)),
]
