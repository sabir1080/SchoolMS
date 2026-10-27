from django.db import transaction
from django.db.models import ProtectedError
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.core.mixins import TenantScopedViewSetMixin
from apps.core.permissions import HasRole, IsInstituteAdmin
from apps.subscriptions.features import Feature
from apps.subscriptions.gating import ActiveSubscription, RequiresFeature

from .models import Employee, Payslip, PayslipStatus
from .serializers import EmployeeSerializer, GenerateInputSerializer, PayInputSerializer, PayslipSerializer


def money(value):
    return f"{value:.2f}"


class EmployeeViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """Staff on the payroll (admins only)."""

    queryset = Employee.objects.select_related("user")
    serializer_class = EmployeeSerializer
    permission_classes = [IsInstituteAdmin]
    required_feature = Feature.PAYROLL
    pagination_class = None

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError("This staff member has salary records. Untick “Active” instead of deleting.")


class PayslipViewSet(TenantScopedViewSetMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Monthly salaries. ?period=YYYY-MM. Make the month's slips, adjust bonus/deductions, then mark them paid."""

    queryset = Payslip.objects.select_related("employee")
    serializer_class = PayslipSerializer
    permission_classes = [IsInstituteAdmin]
    required_feature = Feature.PAYROLL
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list" and self.request.query_params.get("period"):
            queryset = queryset.filter(period=self.request.query_params["period"])
        return queryset

    def list(self, request, *args, **kwargs):
        slips = list(self.get_queryset())
        paid = [s for s in slips if s.status == PayslipStatus.PAID]
        return Response({
            "results": PayslipSerializer(slips, many=True).data,
            "summary": {
                "count": len(slips), "paid_count": len(paid),
                "total": money(sum((s.net for s in slips), 0)), "paid": money(sum((s.net for s in paid), 0)),
                "unpaid": money(sum((s.net for s in slips if s.status != PayslipStatus.PAID), 0)),
            },
        })

    def perform_destroy(self, instance):
        if instance.status == PayslipStatus.PAID:
            raise ValidationError("A paid salary cannot be deleted. Undo the payment first.")
        instance.delete()

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """Make slips for every active staff member who has none for the month yet."""
        serializer = GenerateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        period, tenant = serializer.validated_data["period"], self.get_tenant()
        with transaction.atomic():
            existing = set(Payslip.objects.filter(tenant=tenant, period=period).values_list("employee_id", flat=True))
            new = [
                Payslip(tenant=tenant, employee=e, period=period, basic=e.basic_salary, allowance=e.allowance)
                for e in Employee.objects.filter(tenant=tenant, is_active=True).exclude(id__in=existing)
            ]
            Payslip.objects.bulk_create(new)
        return Response({"created": len(new), "already": len(existing)})

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        slip = self.get_object()
        if slip.status == PayslipStatus.PAID:
            raise ValidationError("Already paid.")
        data = PayInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        slip.status, slip.paid_by = PayslipStatus.PAID, request.user
        slip.paid_on, slip.method, slip.reference = data.validated_data["date"], data.validated_data["method"], data.validated_data["reference"]
        slip.save()
        return Response(PayslipSerializer(slip).data)

    @action(detail=True, methods=["post"])
    def unpay(self, request, pk=None):
        slip = self.get_object()
        slip.status, slip.paid_on, slip.method, slip.reference, slip.paid_by = PayslipStatus.UNPAID, None, "", "", None
        slip.save()
        return Response(PayslipSerializer(slip).data)


class MyPayslipsView(APIView):
    """A teacher's (or admin's) own salary slips, when their login is linked to a staff record."""

    required_feature = Feature.PAYROLL

    def get_permissions(self):
        return [HasRole.for_roles(Role.TEACHER, Role.ADMIN)(), ActiveSubscription(), RequiresFeature()]

    def get(self, request):
        employee = getattr(request.user, "employee_profile", None)
        if employee is None:
            return Response({"linked": False, "results": []})
        slips = Payslip.objects.filter(employee=employee).select_related("employee")
        return Response({"linked": True, "results": PayslipSerializer(slips, many=True).data})
