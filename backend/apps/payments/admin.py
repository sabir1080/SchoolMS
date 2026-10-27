from django.contrib import admin

from .models import GatewayAccount, OnlinePayment


@admin.register(OnlinePayment)
class OnlinePaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "provider", "amount", "status", "tenant", "created_at")
    list_filter = ("provider", "status", "tenant")


@admin.register(GatewayAccount)
class GatewayAccountAdmin(admin.ModelAdmin):
    list_display = ("tenant", "provider", "is_enabled", "test_mode")
    exclude = ("password", "secret")
