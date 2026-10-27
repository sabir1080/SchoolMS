from django.urls import path

from .views import (
    DemoCompleteView,
    EasypaisaIPNView,
    EasypaisaPostbackView,
    JazzCashReturnView,
    PaymentAttemptsView,
    PaymentSettingsView,
    PaymentStatusView,
    SafepayReturnView,
    StripeReturnView,
    StripeWebhookView,
    PayOptionsView,
    StartPaymentView,
)

urlpatterns = [
    path("pay/settings/", PaymentSettingsView.as_view(), name="pay-settings"),
    path("pay/options/", PayOptionsView.as_view(), name="pay-options"),
    path("pay/start/", StartPaymentView.as_view(), name="pay-start"),
    path("pay/status/", PaymentStatusView.as_view(), name="pay-status"),
    path("pay/attempts/", PaymentAttemptsView.as_view(), name="pay-attempts"),
    path("pay/demo/complete/", DemoCompleteView.as_view(), name="pay-demo-complete"),
    path("pay/jazzcash/return/", JazzCashReturnView.as_view(), name="pay-jazzcash-return"),
    path("pay/easypaisa/postback/", EasypaisaPostbackView.as_view(), name="pay-easypaisa-postback"),
    path("pay/easypaisa/ipn/", EasypaisaIPNView.as_view(), name="pay-easypaisa-ipn"),
    path("pay/stripe/return/", StripeReturnView.as_view(), name="pay-stripe-return"),
    path("pay/stripe/webhook/<str:code>/", StripeWebhookView.as_view(), name="pay-stripe-webhook"),
    path("pay/safepay/return/", SafepayReturnView.as_view(), name="pay-safepay-return"),
]
