from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsInstituteAdmin, IsSuperAdmin
from apps.subscriptions.models import BillingCycle, Plan

from . import services
from .models import Kind, ProviderProfile, SignedAgreement, Status


class AgreementSerializer(serializers.ModelSerializer):
    number = serializers.CharField(read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True, default=None)
    institute_code = serializers.CharField(source="tenant.slug", read_only=True)
    payment_method = serializers.CharField(source="payment.get_method_display", read_only=True, default=None)
    payment_paid_at = serializers.DateTimeField(source="payment.created_at", read_only=True, default=None)
    payment_reference_recorded = serializers.CharField(source="payment.reference", read_only=True, default=None)

    class Meta:
        model = SignedAgreement
        fields = [
            "id", "number", "tenant", "kind", "kind_label", "version", "status", "status_label", "plan", "plan_name", "billing_cycle",
            "amount", "currency", "institute_code", "institute_legal_name", "institute_address", "signer_name",
            "signer_designation", "signer_cnic", "signer_phone", "signature", "signed_at", "ip_address", "provider",
            "schedule", "sections", "payment_reference", "payment_method", "payment_paid_at", "payment_reference_recorded",
            "period_start", "period_end", "activated_at",
        ]


class SignSerializer(serializers.Serializer):
    plan = serializers.SlugRelatedField(slug_field="code", queryset=Plan.objects.filter(is_active=True, is_public=True))
    billing_cycle = serializers.ChoiceField(choices=BillingCycle.choices)
    institute_legal_name = serializers.CharField(max_length=200)
    institute_address = serializers.CharField(max_length=255)
    signer_name = serializers.CharField(max_length=150)
    signer_designation = serializers.CharField(max_length=100)
    signer_cnic = serializers.CharField(max_length=30)
    signer_phone = serializers.CharField(max_length=30)
    signature = serializers.CharField(max_length=150)
    accept = serializers.BooleanField()
    payment_reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")

    def validate_accept(self, value):
        if not value:
            raise serializers.ValidationError("Please tick that you agree to the agreement.")
        return value

    def validate_signer_cnic(self, value):
        digits = "".join(c for c in value if c.isdigit())
        if len(digits) != 13:
            raise serializers.ValidationError("Enter the 13-digit CNIC, e.g. 35202-1234567-1.")
        return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"

    def validate(self, attrs):
        for field in ("institute_legal_name", "institute_address", "signer_name", "signer_designation", "signature"):
            attrs[field] = attrs[field].strip()
        if " ".join(attrs["signature"].lower().split()) != " ".join(attrs["signer_name"].lower().split()):
            raise serializers.ValidationError({"signature": ["Type your full name exactly as above to sign."]})
        if services.price_for(attrs["plan"], attrs["billing_cycle"], self.context["tenant"].currency)[0] is None:
            raise serializers.ValidationError({"plan": ["This plan has no price for your currency. Please contact us."]})
        return attrs


class PublicTrialAgreementView(APIView):
    """The free trial agreement, for the registration page."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(services.trial_document())


class InstituteAgreementsView(APIView):
    """An institute admin's agreements (works even after the subscription expired, to renew)."""

    permission_classes = [IsInstituteAdmin]

    def get(self, request):
        agreements = SignedAgreement.objects.filter(tenant=request.user.tenant).select_related("plan", "payment", "tenant")
        return Response(AgreementSerializer(agreements, many=True).data)

    def post(self, request):
        """Sign a subscription agreement (it then waits for the payment)."""
        tenant = request.user.tenant
        serializer = SignSerializer(data=request.data, context={"tenant": tenant})
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        plan, cycle = data.pop("plan"), data.pop("billing_cycle")
        data.pop("accept")
        agreement = services.sign_subscription(tenant, request.user, request, plan, cycle, data)
        return Response(AgreementSerializer(agreement).data, status=status.HTTP_201_CREATED)


class InstituteAgreementPreviewView(APIView):
    """The subscription agreement as it would be signed now, details from the last agreement, and how to pay."""

    permission_classes = [IsInstituteAdmin]

    def get(self, request):
        tenant = request.user.tenant
        plan = Plan.objects.filter(code=request.query_params.get("plan", ""), is_active=True, is_public=True).first()
        cycle = request.query_params.get("cycle", "monthly")
        if plan is None or cycle not in BillingCycle.values:
            raise ValidationError("Choose a plan and billing cycle.")
        doc = services.subscription_document(plan, cycle, tenant.currency)
        last = SignedAgreement.objects.filter(tenant=tenant, kind=Kind.SUBSCRIPTION).exclude(status=Status.CANCELLED).first()
        prefill = {
            "institute_legal_name": last.institute_legal_name if last else tenant.name,
            "institute_address": last.institute_address if last else tenant.address,
            "signer_name": last.signer_name if last else request.user.get_full_name(),
            "signer_designation": last.signer_designation if last else "",
            "signer_cnic": last.signer_cnic if last else "",
            "signer_phone": last.signer_phone if last else tenant.phone,
        }
        return Response({**doc, "amount": doc["amount"] and f"{doc['amount']:.2f}", "prefill": prefill,
                         "renewal": bool(last and last.plan_id == plan.id and last.version == doc["version"]),
                         "payment_instructions": ProviderProfile.get().payment_instructions})


class InstituteAgreementDetailView(APIView):
    permission_classes = [IsInstituteAdmin]

    def agreement(self, request, pk):
        agreement = SignedAgreement.objects.filter(tenant=request.user.tenant, pk=pk).select_related("plan", "payment", "tenant").first()
        if agreement is None:
            raise NotFound("Agreement not found.")
        return agreement

    def get(self, request, pk):
        agreement = self.agreement(request, pk)
        return Response({**AgreementSerializer(agreement).data, "payment_instructions": ProviderProfile.get().payment_instructions
                         if agreement.status == Status.PENDING else ""})

    def post(self, request, pk):
        """``action``: ``reference`` (tell us the payment reference) or ``cancel`` (withdraw an unpaid agreement)."""
        agreement = self.agreement(request, pk)
        if agreement.status != Status.PENDING:
            raise ValidationError("Only an agreement waiting for payment can be changed.")
        if request.data.get("action") == "cancel":
            agreement.status = Status.CANCELLED
            agreement.save(update_fields=["status", "updated_at"])
        else:
            agreement.payment_reference = str(request.data.get("payment_reference", "")).strip()[:100]
            agreement.save(update_fields=["payment_reference", "updated_at"])
        return Response(AgreementSerializer(agreement).data)


class AcceptTrialView(APIView):
    """Institutes the platform owner created accept the free trial agreement on first visit."""

    permission_classes = [IsInstituteAdmin]

    def post(self, request):
        tenant = request.user.tenant
        if SignedAgreement.objects.filter(tenant=tenant).exists():
            raise ValidationError("An agreement is already in place.")
        name = str(request.data.get("signer_name", "")).strip()
        if not request.data.get("accept") or not name:
            raise ValidationError("Type your full name and tick that you agree.")
        agreement = services.accept_trial(tenant, request.user, request, name[:150])
        return Response(AgreementSerializer(agreement).data, status=status.HTTP_201_CREATED)


class ProviderProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderProfile
        fields = ["business_name", "owner_name", "address", "phone", "email", "payment_instructions", "grace_days",
                  "data_retention_days", "refund_policy"]
        extra_kwargs = {"grace_days": {"max_value": 60}, "data_retention_days": {"min_value": 30, "max_value": 3650}}


class ProviderProfileView(APIView):
    """The platform owner's business details and terms for new agreements."""

    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response(ProviderProfileSerializer(ProviderProfile.get()).data)

    def patch(self, request):
        serializer = ProviderProfileSerializer(ProviderProfile.get(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PlatformAgreementsView(APIView):
    """All agreements (``?tenant=`` for one institute, ``?status=pending_payment`` for those waiting for payment)."""

    permission_classes = [IsSuperAdmin]

    def get(self, request):
        agreements = SignedAgreement.objects.select_related("plan", "payment", "tenant")
        if request.query_params.get("tenant"):
            agreements = agreements.filter(tenant_id=request.query_params["tenant"])
        if request.query_params.get("status"):
            agreements = agreements.filter(status=request.query_params["status"])
        return Response(AgreementSerializer(agreements[:200], many=True).data)


class PlatformAgreementDetailView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, pk):
        agreement = SignedAgreement.objects.select_related("plan", "payment", "tenant").filter(pk=pk).first()
        if agreement is None:
            raise NotFound("Agreement not found.")
        return Response(AgreementSerializer(agreement).data)
