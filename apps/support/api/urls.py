from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.support.api.views import TicketViewSet

router = DefaultRouter()
router.register("tickets", TicketViewSet, basename="ticket")

urlpatterns = [path("", include(router.urls))]
