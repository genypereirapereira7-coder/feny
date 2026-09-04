from django.urls import path

from apps.reports.api.views import RevenueByMonthView

urlpatterns = [path("revenue-by-month/", RevenueByMonthView.as_view(), name="report-revenue-by-month")]
