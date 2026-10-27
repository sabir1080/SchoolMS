from decimal import Decimal

from rest_framework import serializers

from apps.academics.models import AcademicSession, Program, Section
from apps.core.serializers import TenantPrimaryKeyRelatedField
from apps.students.models import Student

from .models import FeeHead, Invoice, InvoiceItem, InvoiceStatus, Payment, PaymentMethod, StudentDiscount

MONEY = {"max_digits": 12, "decimal_places": 2}


class FeeHeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeHead
        fields = ["id", "name", "frequency", "is_active", "sort_order"]

    def validate_name(self, value):
        value = value.strip()
        tenant = self.context["request"].user.tenant
        taken = FeeHead.objects.filter(tenant=tenant, name__iexact=value)
        if self.instance is not None:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError(f'"{value}" already exists.')
        return value


class RateInputSerializer(serializers.Serializer):
    fee_head = TenantPrimaryKeyRelatedField(queryset=FeeHead.objects.all())
    amount = serializers.DecimalField(min_value=Decimal(0), **MONEY)


class SetRatesSerializer(serializers.Serializer):
    """Set every fee for one program and session at once (amount 0 removes a fee)."""

    session = TenantPrimaryKeyRelatedField(queryset=AcademicSession.objects.all())
    program = TenantPrimaryKeyRelatedField(queryset=Program.objects.all())
    rates = RateInputSerializer(many=True)


class StudentDiscountSerializer(serializers.ModelSerializer):
    student = TenantPrimaryKeyRelatedField(queryset=Student.objects.all())
    fee_head = TenantPrimaryKeyRelatedField(queryset=FeeHead.objects.all())
    fee_head_name = serializers.CharField(source="fee_head.name", read_only=True)

    class Meta:
        model = StudentDiscount
        fields = ["id", "student", "fee_head", "fee_head_name", "discount_type", "value", "reason"]

    def validate(self, attrs):
        kind = attrs.get("discount_type", getattr(self.instance, "discount_type", "amount"))
        value = attrs.get("value", getattr(self.instance, "value", Decimal(0)))
        if value <= 0:
            raise serializers.ValidationError({"value": ["Must be more than 0."]})
        if kind == "percent" and value > 100:
            raise serializers.ValidationError({"value": ["A percentage cannot be more than 100."]})
        student = attrs.get("student", getattr(self.instance, "student", None))
        head = attrs.get("fee_head", getattr(self.instance, "fee_head", None))
        taken = StudentDiscount.objects.filter(student=student, fee_head=head)
        if self.instance is not None:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError({"fee_head": ["This student already has a discount on this fee."]})
        return attrs


class InvoiceItemSerializer(serializers.ModelSerializer):
    net = serializers.DecimalField(read_only=True, **MONEY)

    class Meta:
        model = InvoiceItem
        fields = ["id", "fee_head", "description", "amount", "discount", "net"]


class PaymentSerializer(serializers.ModelSerializer):
    received_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ["id", "receipt_number", "amount", "date", "method", "reference", "received_by_name", "created_at"]

    def get_received_by_name(self, payment):
        user = payment.received_by
        return (user.get_full_name() or user.username) if user else None


def student_brief(student):
    enrollment = None
    for e in student.enrollments.all():
        if enrollment is None or e.session.start_date > enrollment.session.start_date:
            enrollment = e
    return {
        "id": student.id,
        "full_name": student.full_name,
        "admission_no": student.admission_no,
        "class_name": f"{enrollment.section.program.name} - {enrollment.section.name}" if enrollment else None,
    }


class InvoiceListSerializer(serializers.ModelSerializer):
    student = serializers.SerializerMethodField()
    balance = serializers.DecimalField(read_only=True, **MONEY)

    class Meta:
        model = Invoice
        fields = ["id", "number", "student", "period", "title", "issue_date", "due_date", "total", "paid", "balance", "status"]

    def get_student(self, invoice):
        return student_brief(invoice.student)


class InvoiceDetailSerializer(InvoiceListSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)

    class Meta(InvoiceListSerializer.Meta):
        fields = InvoiceListSerializer.Meta.fields + ["items", "payments", "session_name", "notes"]


class GenerateSerializer(serializers.Serializer):
    session = TenantPrimaryKeyRelatedField(queryset=AcademicSession.objects.all())
    month = serializers.RegexField(r"^\d{4}-(0[1-9]|1[0-2])$", error_messages={"invalid": "Use the format YYYY-MM."})
    issue_date = serializers.DateField()
    due_date = serializers.DateField()
    sections = TenantPrimaryKeyRelatedField(queryset=Section.objects.all(), many=True, required=False)

    def validate(self, attrs):
        if attrs["due_date"] < attrs["issue_date"]:
            raise serializers.ValidationError({"due_date": ["Due date cannot be before the issue date."]})
        if any(s.session_id != attrs["session"].id for s in attrs.get("sections", [])):
            raise serializers.ValidationError({"sections": ["Sections must belong to the chosen session."]})
        return attrs


class ManualItemSerializer(serializers.Serializer):
    fee_head = TenantPrimaryKeyRelatedField(queryset=FeeHead.objects.all(), required=False, allow_null=True)
    description = serializers.CharField(max_length=150)
    amount = serializers.DecimalField(min_value=Decimal("0.01"), max_digits=10, decimal_places=2)
    discount = serializers.DecimalField(min_value=Decimal(0), max_digits=10, decimal_places=2, default=Decimal(0))

    def validate(self, attrs):
        if attrs["discount"] > attrs["amount"]:
            raise serializers.ValidationError({"discount": ["Discount cannot be more than the amount."]})
        return attrs


class ManualInvoiceSerializer(serializers.Serializer):
    student = TenantPrimaryKeyRelatedField(queryset=Student.objects.all())
    session = TenantPrimaryKeyRelatedField(queryset=AcademicSession.objects.all())
    title = serializers.CharField(max_length=100)
    issue_date = serializers.DateField()
    due_date = serializers.DateField()
    notes = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    items = ManualItemSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        if attrs["due_date"] < attrs["issue_date"]:
            raise serializers.ValidationError({"due_date": ["Due date cannot be before the issue date."]})
        return attrs


class PaymentInputSerializer(serializers.Serializer):
    amount = serializers.DecimalField(min_value=Decimal("0.01"), **MONEY)
    date = serializers.DateField()
    method = serializers.ChoiceField(choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        invoice = self.context["invoice"]
        if invoice.status == InvoiceStatus.CANCELLED:
            raise serializers.ValidationError("This invoice is cancelled.")
        if attrs["amount"] > invoice.balance:
            raise serializers.ValidationError({"amount": [f"Only {invoice.balance} is left to pay on this invoice."]})
        return attrs
