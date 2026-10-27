from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EmployeeViewSet, MyPayslipsView, PayslipViewSet

router = DefaultRouter()
router.register("payroll/employees", EmployeeViewSet, basename="employee")
router.register("payroll/payslips", PayslipViewSet, basename="payslip")

urlpatterns = [
    path("me/payslips/", MyPayslipsView.as_view(), name="my-payslips"),
    *router.urls,
]
