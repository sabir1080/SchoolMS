from django.contrib import admin

from .models import AcademicSession, Program, Section, Subject


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "start_date", "end_date", "is_current")
    list_filter = ("tenant",)


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "sort_order", "is_active")
    list_filter = ("tenant",)


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("name", "program", "session", "tenant", "is_active")
    list_filter = ("tenant",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "tenant", "is_active")
    list_filter = ("tenant",)
