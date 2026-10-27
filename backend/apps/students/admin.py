from django.contrib import admin

from .models import Enrollment, Guardian, Student, StudentGuardian


class StudentGuardianInline(admin.TabularInline):
    model = StudentGuardian
    extra = 0


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("admission_no", "first_name", "last_name", "tenant", "status")
    list_filter = ("tenant", "status")
    search_fields = ("first_name", "last_name", "admission_no")
    inlines = [StudentGuardianInline]


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "tenant")
    list_filter = ("tenant",)
    search_fields = ("name", "phone")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "section", "session", "roll_number", "tenant")
    list_filter = ("tenant",)
