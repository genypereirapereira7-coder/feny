from django.urls import path

from apps.dashboard.api.views import DashboardSummaryView

urlpatterns = [path("summary/", DashboardSummaryView.as_view(), name="dashboard-summary")]
