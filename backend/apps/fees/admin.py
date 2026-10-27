from django.contrib import admin

from .models import FeeHead, FeeRate, Invoice, InvoiceItem, Payment, StudentDiscount


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "student", "title", "total", "paid", "status", "tenant")
    list_filter = ("tenant", "status")
    inlines = [InvoiceItemInline]


admin.site.register([FeeHead, FeeRate, StudentDiscount, Payment])
