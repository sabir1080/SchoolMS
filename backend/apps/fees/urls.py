from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    FeeHeadViewSet,
    FeeRatesView,
    FeeSummaryView,
    InvoiceViewSet,
    MyInvoicesView,
    PaymentViewSet,
    ReceiptView,
    StudentDiscountViewSet,
)

router = DefaultRouter()
router.register("fees/heads", FeeHeadViewSet, basename="fee-head")
router.register("fees/discounts", StudentDiscountViewSet, basename="fee-discount")
router.register("fees/invoices", InvoiceViewSet, basename="invoice")
router.register("fees/payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("fees/rates/", FeeRatesView.as_view(), name="fee-rates"),
    path("fees/summary/", FeeSummaryView.as_view(), name="fee-summary"),
    path("fees/receipts/<int:pk>/", ReceiptView.as_view(), name="fee-receipt"),
    path("me/invoices/", MyInvoicesView.as_view(), name="my-invoices"),
    *router.urls,
]
