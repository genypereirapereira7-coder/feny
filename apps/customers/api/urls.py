from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.customers.api.views import CustomerContactViewSet, CustomerViewSet

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customer")
router.register("customer-contacts", CustomerContactViewSet, basename="customer-contact")

urlpatterns = [path("", include(router.urls))]
