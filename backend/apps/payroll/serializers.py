from decimal import Decimal

from rest_framework import serializers

from apps.accounts.models import Role, User
from apps.core.serializers import TenantPrimaryKeyRelatedField
from apps.fees.models import PaymentMethod

from .models import Employee, Payslip

money = dict(max_digits=12, decimal_places=2, min_value=Decimal(0))


class EmployeeSerializer(serializers.ModelSerializer):
    user = TenantPrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False)
    user_name = serializers.CharField(source="user.username", read_only=True, default=None)
    basic_salary = serializers.DecimalField(**money)
    allowance = serializers.DecimalField(**money, required=False)

    class Meta:
        model = Employee
        fields = ["id", "name", "designation", "phone", "cnic", "join_date", "basic_salary", "allowance", "bank_account", "user", "user_name", "is_active"]

    def validate_user(self, user):
        if user is None:
            return user
        if user.role not in (Role.TEACHER, Role.ADMIN):
            raise serializers.ValidationError("Only staff logins can be linked.")
        taken = Employee.objects.filter(user=user)
        if self.instance is not None:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError("This login is already linked to another staff member.")
        return user

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Enter the name.")
        return value


class PayslipSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.name", read_only=True)
    designation = serializers.CharField(source="employee.designation", read_only=True)
    bank_account = serializers.CharField(source="employee.bank_account", read_only=True)
    gross = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    net = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    method_label = serializers.CharField(source="get_method_display", read_only=True)
    bonus = serializers.DecimalField(**money, required=False)
    deduction = serializers.DecimalField(**money, required=False)

    class Meta:
        model = Payslip
        fields = [
            "id", "employee", "employee_name", "designation", "bank_account", "period", "basic", "allowance", "bonus",
            "deduction", "note", "gross", "net", "status", "paid_on", "method", "method_label", "reference",
        ]
        read_only_fields = ["employee", "period", "basic", "allowance", "status", "paid_on", "method", "reference"]

    def validate(self, attrs):
        if self.instance is not None and self.instance.status == "paid":
            raise serializers.ValidationError("This salary is already paid. Undo the payment first to change it.")
        bonus = attrs.get("bonus", getattr(self.instance, "bonus", 0))
        deduction = attrs.get("deduction", getattr(self.instance, "deduction", 0))
        if self.instance is not None and deduction > self.instance.basic + self.instance.allowance + bonus:
            raise serializers.ValidationError({"deduction": ["The deduction cannot be more than the salary."]})
        return attrs


class PayInputSerializer(serializers.Serializer):
    date = serializers.DateField()
    method = serializers.ChoiceField(choices=PaymentMethod.choices)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")


class GenerateInputSerializer(serializers.Serializer):
    period = serializers.RegexField(r"^\d{4}-(0[1-9]|1[0-2])$", error_messages={"invalid": "Use the format YYYY-MM."})
