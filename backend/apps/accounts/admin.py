from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "tenant", "is_active")
    list_filter = ("role", "tenant", "is_active")
    fieldsets = DjangoUserAdmin.fieldsets + (("Institute", {"fields": ("role", "tenant", "phone")}),)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Institute", {"fields": ("email", "role", "tenant", "phone")}),
    )
