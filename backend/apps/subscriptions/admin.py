from django.contrib import admin

from .models import Plan, PlanPrice, Subscription, SubscriptionPayment


class PlanPriceInline(admin.TabularInline):
    model = PlanPrice
    extra = 1


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "max_students", "max_staff", "is_public", "is_active", "sort_order")
    inlines = [PlanPriceInline]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("tenant", "plan", "status", "billing_cycle", "current_period_end")
    list_filter = ("status", "plan")


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = ("subscription", "plan", "amount", "currency", "method", "created_at")
    list_filter = ("method", "currency")
