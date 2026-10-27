from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.academics.models import Section
from apps.accounts.models import User
from apps.accounts.passwords import check_password, policy_for
from apps.core.serializers import TenantPrimaryKeyRelatedField

from .models import Enrollment, Guardian, Relation, Student, StudentGuardian, StudentStatus
from .services import (
    check_student_limit,
    enroll,
    lock_tenant,
    next_admission_number,
    sync_login_status,
)


class EnrollmentSerializer(serializers.ModelSerializer):
    program = serializers.IntegerField(source="section.program_id", read_only=True)
    program_name = serializers.CharField(source="section.program.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    is_current = serializers.BooleanField(source="session.is_current", read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            "id", "section", "section_name", "program", "program_name", "session", "session_name",
            "is_current", "roll_number", "enrolled_on",
        ]


class EnrollInputSerializer(serializers.Serializer):
    section = TenantPrimaryKeyRelatedField(queryset=Section.objects.select_related("session"))
    roll_number = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        section = attrs["section"]
        roll = attrs["roll_number"].strip()
        attrs["roll_number"] = roll
        if roll:
            taken = Enrollment.objects.filter(section=section, roll_number=roll)
            student = self.context.get("student")
            if student is not None:
                taken = taken.exclude(student=student)
            if taken.exists():
                raise serializers.ValidationError({"roll_number": [f"Roll number {roll} is already used in this section."]})
        return attrs


class GuardianInputSerializer(serializers.Serializer):
    """A guardian in the admission form: new details, or ``id`` of an existing guardian (siblings)."""

    id = serializers.IntegerField(required=False)
    name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    cnic = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    occupation = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    relation = serializers.ChoiceField(choices=Relation.choices, default=Relation.FATHER)
    is_primary = serializers.BooleanField(default=False)


GUARDIAN_FIELDS = ("name", "phone", "cnic", "email", "occupation")


class StudentWriteSerializer(serializers.ModelSerializer):
    guardians = GuardianInputSerializer(many=True, required=False, write_only=True)
    enrollment = EnrollInputSerializer(required=False, write_only=True, allow_null=True)
    admission_no = serializers.CharField(max_length=30, required=False, allow_blank=True)

    class Meta:
        model = Student
        fields = [
            "id", "admission_no", "first_name", "last_name", "gender", "date_of_birth", "id_number",
            "blood_group", "phone", "email", "address", "admission_date", "previous_school", "status",
            "notes", "guardians", "enrollment",
        ]

    @property
    def tenant(self):
        return self.context["request"].user.tenant

    def validate_admission_no(self, value):
        value = value.strip()
        if value:
            taken = Student.objects.filter(tenant=self.tenant, admission_no__iexact=value)
            if self.instance is not None:
                taken = taken.exclude(pk=self.instance.pk)
            if taken.exists():
                raise serializers.ValidationError("This admission number is already used.")
        return value

    def validate_guardians(self, guardians):
        ids = [g["id"] for g in guardians if g.get("id")]
        if ids:
            found = set(Guardian.objects.filter(tenant=self.tenant, pk__in=ids).values_list("pk", flat=True))
            if found != set(ids):
                raise serializers.ValidationError("Guardian not found.")
        if guardians and not any(g.get("is_primary") for g in guardians):
            guardians[0]["is_primary"] = True
        return guardians

    def _save_guardians(self, student, guardians):
        StudentGuardian.objects.filter(student=student).delete()
        for data in guardians:
            # .get(): on PATCH the nested defaults are not applied.
            details = {f: data.get(f, "") for f in GUARDIAN_FIELDS}
            guardian = None
            if data.get("id"):
                guardian = Guardian.objects.get(tenant=student.tenant, pk=data["id"])
                for field, value in details.items():
                    if value:
                        setattr(guardian, field, value)
                guardian.save()
            elif details["phone"]:
                # Same phone number in this institute = same guardian (e.g. a sibling's father).
                guardian = Guardian.objects.filter(tenant=student.tenant, phone=details["phone"]).first()
            if guardian is None:
                guardian = Guardian.objects.create(tenant=student.tenant, **details)
            StudentGuardian.objects.update_or_create(
                student=student,
                guardian=guardian,
                defaults={
                    "relation": data.get("relation", Relation.FATHER),
                    "is_primary": data.get("is_primary", False),
                },
            )

    @transaction.atomic
    def create(self, validated_data):
        guardians = validated_data.pop("guardians", [])
        enrollment = validated_data.pop("enrollment", None)
        tenant = lock_tenant(self.tenant)
        if validated_data.get("status", StudentStatus.ACTIVE) == StudentStatus.ACTIVE:
            check_student_limit(tenant)
        if not validated_data.get("admission_no"):
            validated_data["admission_no"], validated_data["admission_seq"] = next_admission_number(tenant)
        student = Student.objects.create(tenant=tenant, **validated_data)
        self._save_guardians(student, guardians)
        if enrollment:
            try:
                with transaction.atomic():
                    enroll(student, enrollment["section"], enrollment["roll_number"])
            except IntegrityError:
                raise serializers.ValidationError({"enrollment": {"roll_number": ["Roll number already used."]}})
        return student

    @transaction.atomic
    def update(self, instance, validated_data):
        guardians = validated_data.pop("guardians", None)
        validated_data.pop("enrollment", None)
        if not validated_data.get("admission_no", instance.admission_no):
            validated_data.pop("admission_no", None)
        becoming_active = (
            validated_data.get("status") == StudentStatus.ACTIVE and instance.status != StudentStatus.ACTIVE
        )
        if becoming_active:
            check_student_limit(lock_tenant(instance.tenant), exclude=instance)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        sync_login_status(instance)
        if guardians is not None:
            self._save_guardians(instance, guardians)
        return instance


def current_enrollment(student):
    """The student's enrollment in the current session, else the latest one (uses prefetched data)."""
    enrollments = list(student.enrollments.all())
    for enrollment in enrollments:
        if enrollment.session.is_current:
            return enrollment
    return enrollments[0] if enrollments else None


def primary_link(student):
    links = list(student.guardian_links.all())
    for link in links:
        if link.is_primary:
            return link
    return links[0] if links else None


class StudentListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    current_enrollment = serializers.SerializerMethodField()
    guardian_name = serializers.SerializerMethodField()
    guardian_phone = serializers.SerializerMethodField()
    has_login = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id", "admission_no", "first_name", "last_name", "full_name", "gender", "status",
            "current_enrollment", "guardian_name", "guardian_phone", "has_login",
        ]

    def get_current_enrollment(self, student):
        enrollment = current_enrollment(student)
        return EnrollmentSerializer(enrollment).data if enrollment else None

    def get_guardian_name(self, student):
        link = primary_link(student)
        return link.guardian.name if link else None

    def get_guardian_phone(self, student):
        link = primary_link(student)
        return link.guardian.phone if link else None

    def get_has_login(self, student):
        return student.user_id is not None


class GuardianSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default=None)
    children = serializers.SerializerMethodField()

    class Meta:
        model = Guardian
        fields = ["id", "name", "phone", "cnic", "email", "occupation", "address", "username", "children"]

    def get_children(self, guardian):
        return [{"id": s.id, "full_name": s.full_name, "admission_no": s.admission_no} for s in guardian.students.all()]


class StudentGuardianSerializer(serializers.ModelSerializer):
    guardian = GuardianSerializer(read_only=True)

    class Meta:
        model = StudentGuardian
        fields = ["relation", "is_primary", "guardian"]


class StudentDetailSerializer(StudentListSerializer):
    guardian_links = StudentGuardianSerializer(many=True, read_only=True)
    enrollments = EnrollmentSerializer(many=True, read_only=True)
    username = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta(StudentListSerializer.Meta):
        fields = StudentListSerializer.Meta.fields + [
            "date_of_birth", "id_number", "blood_group", "phone", "email", "address", "admission_date",
            "previous_school", "notes", "guardian_links", "enrollments", "username",
        ]


class CreateLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(trim_whitespace=False)

    def validate_username(self, value):
        value = value.strip()
        if User.objects.filter(tenant=self.context["tenant"], username=value).exists():
            raise serializers.ValidationError("This username is already used in your institute.")
        return value

    def validate(self, attrs):
        candidate = User(username=attrs["username"])
        check_password(attrs["password"], policy_for(self.context["tenant"]), user=candidate)
        return attrs

    def create_user(self, role, first_name, last_name="", email=""):
        data = self.validated_data
        return User.objects.create_user(
            username=data["username"],
            password=data["password"],
            role=role,
            tenant=self.context["tenant"],
            first_name=first_name[:150],
            last_name=last_name[:150],
            email=email,
        )


class MyChildSerializer(serializers.ModelSerializer):
    """What a parent sees about each of their children."""

    full_name = serializers.CharField(read_only=True)
    current_enrollment = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ["id", "admission_no", "full_name", "gender", "date_of_birth", "status", "current_enrollment"]

    def get_current_enrollment(self, student):
        enrollment = current_enrollment(student)
        return EnrollmentSerializer(enrollment).data if enrollment else None

