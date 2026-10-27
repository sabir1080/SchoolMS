from decimal import Decimal

from django.db import transaction
from django.db.models import F, Prefetch, Q, Sum
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.views import BulkCreateByNameMixin
from apps.accounts.models import Role
from apps.core.mixins import TenantScopedViewSetMixin
from apps.core.permissions import HasRole, IsInstituteAdmin
from apps.core.timeutils import parse_month, tenant_today
from apps.students.models import Enrollment
from apps.subscriptions.features import Feature
from apps.subscriptions.gating import ActiveSubscription, RequiresFeature

from .models import FeeHead, FeeRate, Invoice, InvoiceStatus, Payment, StudentDiscount
from .serializers import (
    FeeHeadSerializer,
    GenerateSerializer,
    InvoiceDetailSerializer,
    InvoiceListSerializer,
    ManualInvoiceSerializer,
    PaymentInputSerializer,
    PaymentSerializer,
    SetRatesSerializer,
    StudentDiscountSerializer,
)
from .services import create_invoice, generate_monthly_invoices, record_payment


def money(value):
    """Amounts as strings with two decimals, the same on every database."""
    return f"{Decimal(value or 0):.2f}"


class FeesViewSetMixin(TenantScopedViewSetMixin):
    """Fees are managed by institute admins; the plan must include fees."""

    permission_classes = [IsInstituteAdmin]
    required_feature = Feature.FEES


class FeesAPIView(APIView):
    required_feature = Feature.FEES
    roles = (Role.ADMIN,)

    def get_permissions(self):
        return [HasRole.for_roles(*self.roles)(), ActiveSubscription(), RequiresFeature()]

    @property
    def tenant(self):
        return self.request.user.tenant


class FeeHeadViewSet(BulkCreateByNameMixin, FeesViewSetMixin, viewsets.ModelViewSet):
    queryset = FeeHead.objects.all()
    serializer_class = FeeHeadSerializer


class FeeRatesView(FeesAPIView):
    """GET ?session=: every fee amount in that session. POST: set one program's fees."""

    def rates(self, session_id):
        rates = FeeRate.objects.filter(tenant=self.tenant, session_id=session_id or 0)
        return [{"program": r.program_id, "fee_head": r.fee_head_id, "amount": money(r.amount)} for r in rates]

    def get(self, request):
        return Response(self.rates(request.query_params.get("session")))

    def post(self, request):
        serializer = SetRatesSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        session, program = serializer.validated_data["session"], serializer.validated_data["program"]
        with transaction.atomic():
            for rate in serializer.validated_data["rates"]:
                lookup = {"program": program, "session": session, "fee_head": rate["fee_head"]}
                if rate["amount"] > 0:
                    FeeRate.objects.update_or_create(**lookup, defaults={"tenant": self.tenant, "amount": rate["amount"]})
                else:
                    FeeRate.objects.filter(**lookup).delete()
        return Response(self.rates(session.pk))


class StudentDiscountViewSet(FeesViewSetMixin, viewsets.ModelViewSet):
    queryset = StudentDiscount.objects.select_related("fee_head")
    serializer_class = StudentDiscountSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        student = self.request.query_params.get("student")
        return queryset.filter(student_id=student) if student else queryset


def invoice_queryset():
    return Invoice.objects.select_related("student", "session").prefetch_related(
        Prefetch("student__enrollments", queryset=Enrollment.objects.select_related("section__program", "session")),
        "items",
        Prefetch("payments", queryset=Payment.objects.select_related("received_by")),
    )


class InvoiceViewSet(FeesViewSetMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = invoice_queryset()

    def get_serializer_class(self):
        return InvoiceListSerializer if self.action == "list" else InvoiceDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        p = self.request.query_params
        if p.get("status") == "due":
            queryset = queryset.filter(status__in=[InvoiceStatus.UNPAID, InvoiceStatus.PARTIAL])
        elif p.get("status") == "overdue":
            queryset = queryset.filter(
                status__in=[InvoiceStatus.UNPAID, InvoiceStatus.PARTIAL], due_date__lt=tenant_today(self.get_tenant())
            )
        elif p.get("status"):
            queryset = queryset.filter(status=p["status"])
        if p.get("period"):
            queryset = queryset.filter(period=p["period"])
        if p.get("student"):
            queryset = queryset.filter(student_id=p["student"])
        if p.get("section"):
            queryset = queryset.filter(student__enrollments__section_id=p["section"], student__enrollments__session=F("session"))
        elif p.get("program"):
            queryset = queryset.filter(
                student__enrollments__section__program_id=p["program"], student__enrollments__session=F("session")
            )
        if p.get("search"):
            term = p["search"].strip()
            number = term.lstrip("#").removeprefix("INV-").lstrip("0")
            q = Q(student__first_name__icontains=term) | Q(student__last_name__icontains=term) | Q(student__admission_no__iexact=term)
            if number.isdigit():
                q |= Q(number=int(number))
            queryset = queryset.filter(q)
        return queryset.distinct()

    def create(self, request):
        serializer = ManualInvoiceSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        invoice = create_invoice(
            self.get_tenant(), data["student"], data["session"], data["title"], data["issue_date"], data["due_date"],
            data["items"], data["notes"], user=request.user,
        )
        return Response(self.detail_data(invoice), status=status.HTTP_201_CREATED)

    def detail_data(self, invoice):
        return InvoiceDetailSerializer(invoice_queryset().get(pk=invoice.pk)).data

    @action(detail=False, methods=["post"])
    def generate(self, request):
        serializer = GenerateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        result = generate_monthly_invoices(
            self.get_tenant(), d["session"], d["month"], d["issue_date"], d["due_date"],
            sections=d.get("sections") or None, user=request.user,
        )
        return Response({**result, "total_amount": money(result["total_amount"])})

    @action(detail=True, methods=["post"])
    def payments(self, request, pk=None):
        invoice = self.get_object()
        serializer = PaymentInputSerializer(data=request.data, context={"invoice": invoice})
        serializer.is_valid(raise_exception=True)
        record_payment(invoice, user=request.user, **serializer.validated_data)
        return Response(self.detail_data(invoice), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        invoice = self.get_object()
        if invoice.payments.exists():
            raise ValidationError("This invoice has payments. Delete the payments first.")
        invoice.status = InvoiceStatus.CANCELLED
        invoice.save(update_fields=["status", "updated_at"])
        return Response(self.detail_data(invoice))


class PaymentViewSet(FeesViewSetMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Delete a payment entered by mistake; the invoice is recalculated."""

    queryset = Payment.objects.select_related("invoice")
    serializer_class = PaymentSerializer

    def perform_destroy(self, instance):
        with transaction.atomic():
            invoice = instance.invoice
            instance.delete()
            invoice.refresh_totals()


class FeeSummaryView(FeesAPIView):
    """Money billed and collected in a month, what is still due, and the biggest overdue balances."""

    def get(self, request):
        today = tenant_today(self.tenant)
        month = request.query_params.get("month") or today.strftime("%Y-%m")
        first, last = parse_month(month, today)
        active = Invoice.objects.filter(tenant=self.tenant).exclude(status=InvoiceStatus.CANCELLED)
        billed = active.filter(period=month).aggregate(s=Sum("total"))["s"] or 0
        billed_paid = active.filter(period=month).aggregate(s=Sum("paid"))["s"] or 0
        collected = Payment.objects.filter(tenant=self.tenant, date__range=(first, last)).aggregate(s=Sum("amount"))["s"] or 0
        due = active.filter(status__in=[InvoiceStatus.UNPAID, InvoiceStatus.PARTIAL])
        outstanding = (due.aggregate(s=Sum("total"))["s"] or 0) - (due.aggregate(s=Sum("paid"))["s"] or 0)
        overdue = due.filter(due_date__lt=today)
        by_student = {}
        for inv in overdue.select_related("student"):
            row = by_student.setdefault(
                inv.student_id, {"student": inv.student_id, "full_name": inv.student.full_name,
                                 "admission_no": inv.student.admission_no, "balance": 0, "invoices": 0}
            )
            row["balance"] += inv.balance
            row["invoices"] += 1
        defaulters = sorted(by_student.values(), key=lambda r: r["balance"], reverse=True)
        return Response(
            {
                "month": month,
                "billed": money(billed),
                "billed_paid": money(billed_paid),
                "collection_percentage": round(float(billed_paid) * 100 / float(billed), 1) if billed else None,
                "collected": money(collected),
                "outstanding": money(outstanding),
                "overdue_students": len(defaulters),
                "defaulters": [{**d, "balance": money(d["balance"])} for d in defaulters[:20]],
            }
        )


class MyInvoicesView(ListAPIView):
    """Parents see a child's invoices (``?student=``); students see their own."""

    serializer_class = InvoiceDetailSerializer
    pagination_class = None
    required_feature = Feature.FEES

    def get_permissions(self):
        return [HasRole.for_roles(Role.PARENT, Role.STUDENT)(), ActiveSubscription(), RequiresFeature()]

    def get_queryset(self):
        user = self.request.user
        if user.role == Role.STUDENT:
            student = getattr(user, "student_profile", None)
        else:
            guardian = getattr(user, "guardian_profile", None)
            student = guardian.students.filter(pk=self.request.query_params.get("student") or 0).first() if guardian else None
        if student is None:
            raise NotFound("Student not found.")
        return invoice_queryset().filter(student=student).exclude(status=InvoiceStatus.CANCELLED)
