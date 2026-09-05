from django.urls import path

from apps.core.api.views import IntegrationsStatusView

urlpatterns = [path("integrations/", IntegrationsStatusView.as_view(), name="settings-integrations")]
