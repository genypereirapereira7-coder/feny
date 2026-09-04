from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.api.views import LoginView, TwoFactorConfirmView, TwoFactorSetupView, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("auth/token/", LoginView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/2fa/setup/", TwoFactorSetupView.as_view(), name="2fa-setup"),
    path("auth/2fa/confirm/", TwoFactorConfirmView.as_view(), name="2fa-confirm"),
    path("", include(router.urls)),
]
