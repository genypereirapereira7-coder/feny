from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.finance.api.views import (
    ChargeViewSet,
    CommissionViewSet,
    ExpenseViewSet,
    PaymentViewSet,
    RevenueViewSet,
    SubscriptionViewSet,
)

router = DefaultRouter()
router.register("charges", ChargeViewSet, basename="charge")
router.register("payments", PaymentViewSet, basename="payment")
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("commissions", CommissionViewSet, basename="commission")
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("revenues", RevenueViewSet, basename="revenue")

urlpatterns = [path("", include(router.urls))]
