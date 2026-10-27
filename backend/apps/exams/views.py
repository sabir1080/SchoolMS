from django.db import transaction
from django.db.models import Prefetch
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import Program
from apps.accounts.models import Role
from apps.core.mixins import TenantScopedViewSetMixin
from apps.core.permissions import AdminWriteStaffRead, HasRole
from apps.students.models import Student
from apps.students.serializers import current_enrollment
from apps.students.services import current_session
from apps.subscriptions.features import Feature
from apps.subscriptions.gating import ActiveSubscription, RequiresFeature

from .models import Exam, ExamStatus, ExamSubject, GradeBand, grading_scale
from .serializers import ExamSerializer, GradeBandSerializer, GradingInputSerializer, PaperSerializer, PapersInputSerializer
from .services import default_pass_marks, sync_papers


class ExamViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """Exams in a session. Admins edit; teachers read."""

    queryset = Exam.objects.select_related("session").prefetch_related("programs", "papers")
    serializer_class = ExamSerializer
    permission_classes = [AdminWriteStaffRead]
    required_feature = Feature.EXAMS

    def get_queryset(self):
        queryset = super().get_queryset()
        session = self.request.query_params.get("session")
        if session:
            return queryset.filter(session_id=session)
        if self.action == "list":
            current = current_session(self.get_tenant())
            return queryset.filter(session=current) if current else queryset.none()
        return queryset

    def perform_create(self, serializer):
        with transaction.atomic():
            exam = serializer.save(tenant=self.get_tenant())
            sync_papers(exam)

    def perform_update(self, serializer):
        with transaction.atomic():
            before = set(serializer.instance.programs.values_list("id", flat=True))
            exam = serializer.save()
            after = set(exam.programs.values_list("id", flat=True))
            ExamSubject.objects.filter(exam=exam, program_id__in=before - after).delete()
            sync_papers(exam, Program.objects.filter(pk__in=after - before))

    def program_param(self, exam, value):
        program = exam.programs.filter(pk=value or 0).first()
        if program is None:
            raise ValidationError({"program": ["Choose a class that takes this exam."]})
        return program

    @action(detail=True, methods=["get", "put"])
    def papers(self, request, pk=None):
        """GET ?program=: the papers of one class. PUT: change marks/dates, add or remove subjects."""
        exam = self.get_object()
        if request.method == "GET":
            program = self.program_param(exam, request.query_params.get("program"))
        else:
            if request.user.role != Role.ADMIN:
                self.permission_denied(request, "Only admins can change papers.")
            serializer = PapersInputSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            program = self.program_param(exam, data["program"].pk)
            self.save_papers(exam, program, data)
        papers = ExamSubject.objects.filter(exam=exam, program=program).select_related("subject", "program")
        return Response(PaperSerializer(papers, many=True).data)

    @transaction.atomic
    def save_papers(self, exam, program, data):
        papers = {p.id: p for p in ExamSubject.objects.filter(exam=exam, program=program)}
        for row in data["papers"]:
            paper = papers.get(row["id"])
            if paper is None:
                raise ValidationError({"papers": ["A paper does not belong to this class and exam."]})
            date = row.get("date")
            if date and not (exam.session.start_date <= date <= exam.session.end_date):
                raise ValidationError({"papers": [f"Paper dates must be within the session {exam.session.name}."]})
            for field in ("total_marks", "pass_marks", "date", "start_time"):
                if field in row:
                    setattr(paper, field, row[field])
            paper.save()
        ExamSubject.objects.filter(exam=exam, program=program, pk__in=data["remove"]).delete()
        taken = set(ExamSubject.objects.filter(exam=exam, program=program).values_list("subject_id", flat=True))
        ExamSubject.objects.bulk_create(
            [
                ExamSubject(tenant=exam.tenant, exam=exam, program=program, subject=s,
                            pass_marks=default_pass_marks(100, exam.tenant))
                for s in data["add"] if s.id not in taken
            ]
        )

    @action(detail=True, methods=["get"])
    def datesheet(self, request, pk=None):
        """Papers in date order, for one class (?program=) or all classes."""
        exam = self.get_object()
        papers = ExamSubject.objects.filter(exam=exam).select_related("subject", "program")
        if request.query_params.get("program"):
            papers = papers.filter(program_id=request.query_params["program"])
        return Response({"exam": ExamSerializer(exam).data, "papers": PaperSerializer(papers, many=True).data})


class GradingView(APIView):
    """The institute's grading scale (admins change it; teachers can read it)."""

    def get_permissions(self):
        roles = (Role.ADMIN,) if self.request.method == "PUT" else (Role.ADMIN, Role.TEACHER)
        return [HasRole.for_roles(*roles)(), ActiveSubscription(), RequiresFeature()]

    required_feature = Feature.EXAMS

    def get(self, request):
        return Response(GradeBandSerializer(grading_scale(request.user.tenant), many=True).data)

    def put(self, request):
        serializer = GradingInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant = request.user.tenant
        with transaction.atomic():
            GradeBand.objects.filter(tenant=tenant).delete()
            GradeBand.objects.bulk_create(
                [GradeBand(tenant=tenant, **{**b, "name": b["name"].strip()}) for b in serializer.validated_data["bands"]]
            )
        return self.get(request)


class MyExamsView(APIView):
    """Parents (?student=) and students: date sheets of announced exams in the current session."""

    required_feature = Feature.EXAMS

    def get_permissions(self):
        return [HasRole.for_roles(Role.PARENT, Role.STUDENT)(), ActiveSubscription(), RequiresFeature()]

    def get(self, request):
        user = request.user
        if user.role == Role.STUDENT:
            student = getattr(user, "student_profile", None)
        else:
            guardian = getattr(user, "guardian_profile", None)
            student = guardian.students.filter(pk=request.query_params.get("student") or 0).first() if guardian else None
        if student is None:
            raise NotFound("Student not found.")
        student = Student.objects.prefetch_related("enrollments__session", "enrollments__section").get(pk=student.pk)
        enrollment = current_enrollment(student)
        if enrollment is None or not enrollment.session.is_current:
            return Response([])
        program_id = enrollment.section.program_id
        exams = (
            Exam.objects.filter(session=enrollment.session, programs=program_id)
            .exclude(status=ExamStatus.DRAFT)
            .prefetch_related(
                Prefetch("papers", queryset=ExamSubject.objects.filter(program_id=program_id).select_related("subject", "program"))
            )
        )
        return Response(
            [
                {
                    "id": exam.id, "name": exam.name, "status": exam.status,
                    "start_date": exam.start_date, "end_date": exam.end_date,
                    "papers": PaperSerializer(exam.papers.all(), many=True).data,
                }
                for exam in exams
            ]
        )


