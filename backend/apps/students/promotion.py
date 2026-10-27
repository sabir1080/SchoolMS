"""End-of-year promotion: move a section's students into a new session (next class, same class again,
left or graduated), with suggestions taken from the published results of the year."""

from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import AcademicSession, Program, Section
from apps.accounts.models import Role
from apps.attendance.views import roll_sort_key, section_label
from apps.core.permissions import HasRole
from apps.subscriptions.features import Feature
from apps.subscriptions.gating import ActiveSubscription, RequiresFeature

from .models import Enrollment, StudentStatus
from .services import sync_login_status

ACTIONS = ("promote", "repeat", "left", "graduated", "skip")


def next_program(program):
    """The class after ``program`` in the institute's class order, or None for the last class."""
    ordered = list(Program.objects.filter(tenant=program.tenant, is_active=True).order_by("sort_order", "name"))
    ids = [p.id for p in ordered]
    if program.id not in ids:
        return None
    index = ids.index(program.id)
    return ordered[index + 1] if index + 1 < len(ordered) else None


def year_results(section):
    """(source name, {student id: (result, percentage)}) from the latest published annual result, else the
    latest published exam of the section's class in its session."""
    from apps.exams.models import CombinedResult, CombinedStatus, Exam, ExamStatus
    from apps.exams.results import combined_section_results, section_results

    combined = (
        CombinedResult.objects.filter(session=section.session, status=CombinedStatus.PUBLISHED, components__exam__programs=section.program)
        .distinct().select_related("tenant", "session").prefetch_related("components__exam__programs").order_by("-id").first()
    )
    if combined:
        rows = combined_section_results(combined, section)["students"]
        return combined.name, {r["student"]: (r["result"], r["percentage"]) for r in rows}
    exam = (
        Exam.objects.filter(session=section.session, programs=section.program, status=ExamStatus.PUBLISHED)
        .select_related("tenant").order_by("-end_date", "-start_date", "-id").first()
    )
    if exam:
        rows = section_results(exam, section)["students"]
        return exam.name, {r["student"]: (r["result"], r["percentage"]) for r in rows}
    return None, {}


class DecisionSerializer(serializers.Serializer):
    student = serializers.IntegerField()
    action = serializers.ChoiceField(choices=ACTIONS)


class PromoteSerializer(serializers.Serializer):
    section = serializers.IntegerField()
    to_session = serializers.IntegerField()
    decisions = DecisionSerializer(many=True, allow_empty=False)


class PromotionView(APIView):
    """GET ?section=&to_session=: the section's students with a suggested decision.
    POST: apply the decisions (new enrollments in the target session, or mark students as left/graduated)."""

    required_feature = Feature.STUDENTS

    def get_permissions(self):
        return [HasRole.for_roles(Role.ADMIN)(), ActiveSubscription(), RequiresFeature()]

    def load(self, section_id, session_id):
        tenant = self.request.user.tenant
        section = Section.objects.filter(tenant=tenant, pk=section_id or 0).select_related("program", "session").first()
        if section is None:
            raise ValidationError({"section": ["Choose a section."]})
        to_session = AcademicSession.objects.filter(tenant=tenant, pk=session_id or 0).first()
        if to_session is None:
            raise ValidationError({"to_session": ["Choose the new session. Add it in Academic setup first."]})
        if to_session.pk == section.session_id:
            raise ValidationError({"to_session": ["Choose a different session than the section's own."]})
        return section, to_session

    def target_section(self, section, program, to_session, create=False):
        """The section with the same name for ``program`` in the new session (made if needed)."""
        target = Section.objects.filter(program=program, session=to_session, name=section.name).first()
        if target is None:
            target = Section.objects.filter(program=program, session=to_session).order_by("name").first()
        if target is None and create:
            target = Section.objects.create(tenant=section.tenant, program=program, session=to_session, name=section.name, capacity=section.capacity)
        return target

    def get(self, request):
        section, to_session = self.load(request.query_params.get("section"), request.query_params.get("to_session"))
        upcoming = next_program(section.program)
        source, results = year_results(section)
        enrollments = sorted(Enrollment.objects.filter(section=section, student__status=StudentStatus.ACTIVE).select_related("student"), key=roll_sort_key)
        already = {
            e.student_id: f"{e.section.program.name} - {e.section.name}"
            for e in Enrollment.objects.filter(session=to_session, student__in=[e.student_id for e in enrollments]).select_related("section__program")
        }
        students = []
        for e in enrollments:
            result, percentage = results.get(e.student_id, (None, None))
            suggested = "repeat" if result == "fail" else ("promote" if upcoming else "graduated")
            students.append({
                "student": e.student_id, "full_name": e.student.full_name, "admission_no": e.student.admission_no,
                "roll_number": e.roll_number, "result": result, "percentage": percentage, "suggested": suggested,
                "already": already.get(e.student_id),
            })
        promote_to = self.target_section(section, upcoming, to_session) if upcoming else None
        repeat_in = self.target_section(section, section.program, to_session)
        return Response({
            "section": section_label(section),
            "to_session": {"id": to_session.id, "name": to_session.name},
            "next_program": {"id": upcoming.id, "name": upcoming.name} if upcoming else None,
            "promote_to": f"{upcoming.name} - {promote_to.name if promote_to else section.name}" if upcoming else None,
            "promote_to_new": bool(upcoming and promote_to is None),
            "repeat_in": f"{section.program.name} - {repeat_in.name if repeat_in else section.name}",
            "result_source": source,
            "students": students,
        })

    def post(self, request):
        data = PromoteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        section, to_session = self.load(data.validated_data["section"], data.validated_data["to_session"])
        upcoming = next_program(section.program)
        enrolled = {e.student_id: e for e in Enrollment.objects.filter(section=section).select_related("student")}
        counts = {action: 0 for action in ACTIONS}
        with transaction.atomic():
            targets = {}
            for decision in data.validated_data["decisions"]:
                enrollment = enrolled.get(decision["student"])
                if enrollment is None:
                    raise ValidationError({"decisions": ["Some students are not in this section."]})
                action = decision["action"]
                if action == "promote" and upcoming is None:
                    raise ValidationError({"decisions": [f"{section.program.name} is the last class. Choose Graduated instead."]})
                student = enrollment.student
                if action in ("promote", "repeat"):
                    program = upcoming if action == "promote" else section.program
                    if program.id not in targets:
                        targets[program.id] = self.target_section(section, program, to_session, create=True)
                    target = targets[program.id]
                    existing = Enrollment.objects.filter(student=student, session=to_session).first() or Enrollment(
                        tenant=section.tenant, student=student, session=to_session
                    )
                    existing.section = target
                    taken = Enrollment.objects.filter(section=target, roll_number=enrollment.roll_number).exclude(student=student).exists()
                    existing.roll_number = "" if taken or not enrollment.roll_number else enrollment.roll_number
                    try:
                        with transaction.atomic():
                            existing.save()
                    except IntegrityError:
                        existing.roll_number = ""
                        existing.save()
                elif action in ("left", "graduated"):
                    student.status = StudentStatus.LEFT if action == "left" else StudentStatus.GRADUATED
                    student.save(update_fields=["status", "updated_at"])
                    sync_login_status(student)
                counts[action] += 1
        return Response(counts)
