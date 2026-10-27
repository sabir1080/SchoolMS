from django.contrib import admin

from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "institute_type", "country", "is_active", "created_at")
    list_filter = ("institute_type", "country", "is_active")
    search_fields = ("name", "slug", "email")
    prepopulated_fields = {"slug": ("name",)}
