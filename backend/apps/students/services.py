from django.db import transaction
from django.db.models import Max

from apps.academics.models import AcademicSession
from apps.accounts.models import User
from apps.subscriptions.gating import check_limit
from apps.tenants.models import Tenant

from .models import Enrollment, Student, StudentStatus


def lock_tenant(tenant):
    """Serialise admissions per institute so numbers and plan limits stay correct."""
    return Tenant.objects.select_for_update().get(pk=tenant.pk)


def check_student_limit(tenant, exclude=None):
    active = Student.objects.filter(tenant=tenant, status=StudentStatus.ACTIVE)
    if exclude is not None:
        active = active.exclude(pk=exclude.pk)
    check_limit(tenant, "max_students", active.count())


def next_admission_number(tenant):
    """Return (admission_no, seq) for the next automatic number: 1, 2, 3 ... skipping ones in use."""
    seq = (Student.objects.filter(tenant=tenant).aggregate(m=Max("admission_seq"))["m"] or 0) + 1
    taken = set(Student.objects.filter(tenant=tenant).values_list("admission_no", flat=True))
    while str(seq) in taken:
        seq += 1
    return str(seq), seq


def current_session(tenant):
    return AcademicSession.objects.filter(tenant=tenant, is_current=True).first()


@transaction.atomic
def enroll(student, section, roll_number=""):
    """Put the student in ``section`` for that section's session (replacing any other section that session)."""
    enrollment = Enrollment.objects.filter(student=student, session_id=section.session_id).first()
    if enrollment is None:
        enrollment = Enrollment(tenant=student.tenant, student=student)
    enrollment.section = section
    enrollment.roll_number = roll_number
    enrollment.save()
    return enrollment


def sync_login_status(student):
    """A student's login only works while they are an active student."""
    if student.user_id:
        active = student.status == StudentStatus.ACTIVE
        if student.user.is_active != active:
            User.objects.filter(pk=student.user_id).update(is_active=active)
