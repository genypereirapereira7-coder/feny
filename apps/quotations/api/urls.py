from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.quotations.api.views import QuotationViewSet

router = DefaultRouter()
router.register("quotations", QuotationViewSet, basename="quotation")

urlpatterns = [path("", include(router.urls))]
