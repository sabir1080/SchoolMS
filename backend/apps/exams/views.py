from django.db import transaction
from django.db.models import ProtectedError
from django.db.models import Count, Max, Prefetch, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import Program, Section
from apps.accounts.models import Role
from apps.attendance.views import roll_sort_key, section_label
from apps.core.mixins import TenantScopedViewSetMixin
from apps.core.permissions import AdminWriteStaffRead, HasRole
from apps.recyclebin.mixins import RecycleBinMixin
from apps.recyclebin.services import trash
from apps.students.models import Enrollment, Student, StudentStatus
from apps.students.serializers import current_enrollment
from apps.students.services import current_session
from apps.subscriptions.features import Feature
from apps.subscriptions.gating import ActiveSubscription, RequiresFeature
from apps.timetable.models import TimetableEntry

from .models import CombinedResult, CombinedStatus, Exam, ExamStatus, ExamSubject, GradeBand, Mark, grading_scale
from .serializers import (
    CombinedResultSerializer,
    ExamSerializer,
    GradeBandSerializer,
    GradingInputSerializer,
    MarksInputSerializer,
    PaperSerializer,
    PapersInputSerializer,
)
from .results import combined_result_payload, exam_result_payload
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
        was_published = serializer.instance.status == ExamStatus.PUBLISHED
        self.save_exam(serializer)
        exam = serializer.instance
        if exam.status == ExamStatus.PUBLISHED and not was_published:
            from apps.messaging.alerts import result_alerts

            result_alerts(exam, self.request.user)

    def save_exam(self, serializer):
        with transaction.atomic():
            before = set(serializer.instance.programs.values_list("id", flat=True))
            exam = serializer.save()
            after = set(exam.programs.values_list("id", flat=True))
            if Mark.objects.filter(paper__exam=exam, paper__program_id__in=before - after).exists():
                raise ValidationError({"programs": ["A class you removed already has marks entered."]})
            ExamSubject.objects.filter(exam=exam, program_id__in=before - after).delete()
            sync_papers(exam, Program.objects.filter(pk__in=after - before))

    def perform_destroy(self, instance):
        if Mark.objects.filter(paper__exam=instance).exists():
            raise ValidationError("This exam already has marks and cannot be deleted.")
        try:
            trash(instance, self.request.user)
        except ProtectedError:
            raise ValidationError("This exam is part of an annual result. Remove it there first.")

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
        papers = {p.id: p for p in ExamSubject.objects.filter(exam=exam, program=program).select_related("subject")}
        highest = dict(
            Mark.objects.filter(paper__in=papers).order_by().values("paper").annotate(m=Max("marks_obtained")).values_list("paper", "m")
        )
        for row in data["papers"]:
            paper = papers.get(row["id"])
            if paper is None:
                raise ValidationError({"papers": ["A paper does not belong to this class and exam."]})
            top = highest.get(paper.id)
            if top is not None and "total_marks" in row and row["total_marks"] < top:
                raise ValidationError(
                    {"papers": [f"{paper.subject.name}: a student already has {top.normalize():f} marks, more than the new total."]}
                )
            date = row.get("date")
            if date and not (exam.session.start_date <= date <= exam.session.end_date):
                raise ValidationError({"papers": [f"Paper dates must be within the session {exam.session.name}."]})
            for field in ("total_marks", "pass_marks", "date", "start_time"):
                if field in row:
                    setattr(paper, field, row[field])
            paper.save()
        marked = Mark.objects.filter(paper_id__in=data["remove"], paper__in=papers).select_related("paper__subject").first()
        if marked:
            raise ValidationError({"remove": [f"{marked.paper.subject.name} already has marks and cannot be removed."]})
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


def decimal_text(value):
    """Decimals as strings, the way DRF serializers send them."""
    return None if value is None else str(value)


class MarksView(APIView):
    """Base for marks entry: admins for every section; class teachers for all subjects of their section;
    subject teachers for the subjects they teach a section in the timetable."""

    required_feature = Feature.EXAMS

    def get_permissions(self):
        return [HasRole.for_roles(Role.ADMIN, Role.TEACHER)(), ActiveSubscription(), RequiresFeature()]

    def get_exam(self, exam_id):
        exam = Exam.objects.filter(tenant=self.request.user.tenant, pk=exam_id).select_related("session").first()
        if exam is None:
            raise NotFound("Exam not found.")
        return exam

    def sections(self, exam):
        """Sections of the exam's session and classes this user may enter marks for."""
        sections = Section.objects.filter(
            tenant=exam.tenant, session=exam.session, program__in=exam.programs.all()
        ).select_related("program", "session", "class_teacher")
        if self.request.user.role == Role.TEACHER:
            sections = sections.filter(Q(class_teacher=self.request.user) | Q(timetable__teacher=self.request.user)).distinct()
        return sorted(sections, key=lambda s: (s.program.sort_order, s.program.name, s.name))

    def taught_subjects(self, section):
        """None when the user may enter every subject of the section, else the subject ids they teach there."""
        user = self.request.user
        if user.role != Role.TEACHER or section.class_teacher_id == user.pk:
            return None
        return set(TimetableEntry.objects.filter(section=section, teacher=user).values_list("subject_id", flat=True))

    def get_section(self, exam, section_id):
        section = next((s for s in self.sections(exam) if str(s.id) == str(section_id)), None)
        if section is None:
            if self.request.user.role == Role.TEACHER and Section.objects.filter(tenant=exam.tenant, pk=section_id or 0).exists():
                raise PermissionDenied("Only the class teacher, a teacher of this section or an admin can enter marks here.")
            raise ValidationError({"section": ["Choose a section that takes this exam."]})
        return section

    def get_paper(self, exam, section, paper_id):
        paper = ExamSubject.objects.filter(exam=exam, program=section.program, pk=paper_id or 0).select_related("subject").first()
        if paper is None:
            raise ValidationError({"paper": ["Choose a subject of this class in this exam."]})
        taught = self.taught_subjects(section)
        if taught is not None and paper.subject_id not in taught:
            raise PermissionDenied("You can enter marks only for the subjects you teach in this section.")
        return paper

    def enrollments(self, section):
        rows = Enrollment.objects.filter(section=section, student__status=StudentStatus.ACTIVE).select_related("student")
        return sorted(rows, key=roll_sort_key)


class MarksProgressView(MarksView):
    """For each section the user can see: how many students have marks in each paper."""

    def get(self, request, exam_id):
        exam = self.get_exam(exam_id)
        sections = self.sections(exam)
        taught = {s.id: self.taught_subjects(s) for s in sections}
        papers = list(ExamSubject.objects.filter(exam=exam).select_related("subject"))
        students = dict(
            Enrollment.objects.filter(section__in=sections, student__status=StudentStatus.ACTIVE)
            .order_by().values("section").annotate(n=Count("id")).values_list("section", "n")
        )
        entered = {
            (row["section"], row["paper"]): row["n"]
            for row in Mark.objects.filter(paper__exam=exam, section__in=sections, student__status=StudentStatus.ACTIVE)
            .order_by().values("section", "paper").annotate(n=Count("id"))
        }
        return Response(
            {
                "exam": {"id": exam.id, "name": exam.name, "status": exam.status, "session_name": exam.session.name},
                "can_enter": exam.status == ExamStatus.MARKS_OPEN,
                "sections": [
                    {
                        **section_label(s),
                        "program": s.program_id,
                        "student_count": students.get(s.id, 0),
                        # Results (all subjects together) are for admins and the class teacher.
                        "can_see_result": request.user.role == Role.ADMIN or s.class_teacher_id == request.user.pk,
                        "papers": [
                            {
                                "id": p.id,
                                "subject_name": p.subject.name,
                                "total_marks": decimal_text(p.total_marks),
                                "entered": entered.get((s.id, p.id), 0),
                            }
                            for p in papers
                            if p.program_id == s.program_id and (taught[s.id] is None or p.subject_id in taught[s.id])
                        ],
                    }
                    for s in sections
                ],
            }
        )


class MarksSheetView(MarksView):
    """GET ?section=&paper=: students with their marks. PUT: save the marks (only while marks entry is open)."""

    def sheet(self, exam, section, paper):
        enrollments = self.enrollments(section)
        marks = {m.student_id: m for m in Mark.objects.filter(paper=paper, student__in=[e.student_id for e in enrollments])}
        return {
            "exam": {"id": exam.id, "name": exam.name, "status": exam.status},
            "can_enter": exam.status == ExamStatus.MARKS_OPEN,
            "section": section_label(section),
            "paper": PaperSerializer(paper).data,
            "students": [
                {
                    "student": e.student_id,
                    "admission_no": e.student.admission_no,
                    "full_name": e.student.full_name,
                    "roll_number": e.roll_number,
                    "marks": decimal_text(marks[e.student_id].marks_obtained) if e.student_id in marks else None,
                    "absent": marks[e.student_id].is_absent if e.student_id in marks else False,
                }
                for e in enrollments
            ],
        }

    def get(self, request, exam_id):
        exam = self.get_exam(exam_id)
        section = self.get_section(exam, request.query_params.get("section"))
        paper = self.get_paper(exam, section, request.query_params.get("paper"))
        return Response(self.sheet(exam, section, paper))

    def put(self, request, exam_id):
        exam = self.get_exam(exam_id)
        serializer = MarksInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        section = self.get_section(exam, data["section"])
        paper = self.get_paper(exam, section, data["paper"])
        if exam.status != ExamStatus.MARKS_OPEN:
            raise ValidationError("Marks entry is closed for this exam.")
        enrolled = {e.student_id: e.student for e in self.enrollments(section)}
        errors = []
        for entry in data["entries"]:
            student = enrolled.get(entry["student"])
            if student is None:
                raise ValidationError({"entries": ["Some students are not in this section."]})
            if not entry["absent"] and entry.get("marks") is not None and entry["marks"] > paper.total_marks:
                errors.append(f"{student.full_name}: marks cannot be more than {paper.total_marks.normalize():f}.")
        if errors:
            raise ValidationError({"entries": errors})
        with transaction.atomic():
            for entry in data["entries"]:
                marks = None if entry["absent"] else entry.get("marks")
                if marks is None and not entry["absent"]:
                    Mark.objects.filter(paper=paper, student_id=entry["student"]).delete()
                    continue
                Mark.objects.update_or_create(
                    paper=paper,
                    student_id=entry["student"],
                    defaults={
                        "tenant": exam.tenant,
                        "section": section,
                        "marks_obtained": marks,
                        "is_absent": entry["absent"],
                        "entered_by": request.user,
                    },
                )
        return Response(self.sheet(exam, section, paper))


class ResultsView(MarksView):
    """GET ?section=: the exam result of one section (totals, grades, pass/fail, positions).
    Admins and the section's class teacher only (subject teachers see their own subjects in marks entry)."""

    def sections(self, exam):
        sections = super().sections(exam)
        if self.request.user.role == Role.TEACHER:
            sections = [s for s in sections if s.class_teacher_id == self.request.user.pk]
        return sections

    def get(self, request, exam_id):
        exam = self.get_exam(exam_id)
        section = self.get_section(exam, request.query_params.get("section"))
        return Response(exam_result_payload(exam, section, bool(request.query_params.get("attendance"))))


class CombinedResultViewSet(RecycleBinMixin, TenantScopedViewSetMixin, viewsets.ModelViewSet):
    """Annual (combined) results: exams of a session with weights. Admins edit; teachers read."""

    queryset = CombinedResult.objects.select_related("session").prefetch_related("components__exam")
    serializer_class = CombinedResultSerializer
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
            serializer.save(tenant=self.get_tenant())

    def perform_update(self, serializer):
        with transaction.atomic():
            serializer.save()


class CombinedResultsView(MarksView):
    """GET ?section=: the annual result of one section. Sections: those whose class takes any of its exams."""

    def get_combined(self, combined_id):
        combined = (
            CombinedResult.objects.filter(tenant=self.request.user.tenant, pk=combined_id)
            .select_related("session", "tenant").prefetch_related("components__exam__programs", "components__exam__session")
            .first()
        )
        if combined is None:
            raise NotFound("Annual result not found.")
        return combined

    def sections(self, combined):
        programs = {p.id for c in combined.components.all() for p in c.exam.programs.all()}
        sections = Section.objects.filter(
            tenant=combined.tenant, session=combined.session, program_id__in=programs
        ).select_related("program", "session", "class_teacher")
        if self.request.user.role == Role.TEACHER:
            sections = sections.filter(class_teacher=self.request.user)
        return sorted(sections, key=lambda s: (s.program.sort_order, s.program.name, s.name))

    def get(self, request, combined_id):
        combined = self.get_combined(combined_id)
        sections = self.sections(combined)
        listing = [{**section_label(s), "program": s.program_id} for s in sections]
        section_id = request.query_params.get("section")
        if not section_id:
            return Response({"combined": CombinedResultSerializer(combined).data, "sections": listing})
        section = self.get_section(combined, section_id)
        payload = combined_result_payload(combined, section, bool(request.query_params.get("attendance")))
        return Response({**payload, "sections": listing})


class MyResultsView(APIView):
    """Parents (?student=) and students: published exam results and annual results of the current session."""

    required_feature = Feature.EXAMS

    def get_permissions(self):
        return [HasRole.for_roles(Role.PARENT, Role.STUDENT)(), ActiveSubscription(), RequiresFeature()]

    def get(self, request):
        student = my_student(request)
        enrollment = current_enrollment(student)
        if enrollment is None or not enrollment.session.is_current:
            return Response({"exams": [], "combined": []})
        section = Section.objects.select_related("program", "session", "class_teacher").get(pk=enrollment.section_id)
        exams = (
            Exam.objects.filter(session=enrollment.session, programs=section.program_id, status=ExamStatus.PUBLISHED)
            .select_related("session", "tenant").order_by("start_date", "name")
        )
        combined = (
            CombinedResult.objects.filter(session=enrollment.session, status=CombinedStatus.PUBLISHED,
                                          components__exam__programs=section.program_id)
            .distinct().select_related("session", "tenant").prefetch_related("components__exam__programs")
        )
        return Response(
            {
                "exams": [exam_result_payload(e, section, True, student.pk) for e in exams],
                "combined": [combined_result_payload(c, section, True, student.pk) for c in combined],
            }
        )


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


def my_student(request):
    """The logged-in student, or the parent's child given as ?student=."""
    user = request.user
    if user.role == Role.STUDENT:
        student = getattr(user, "student_profile", None)
    else:
        guardian = getattr(user, "guardian_profile", None)
        student = guardian.students.filter(pk=request.query_params.get("student") or 0).first() if guardian else None
    if student is None:
        raise NotFound("Student not found.")
    return Student.objects.prefetch_related("enrollments__session", "enrollments__section").get(pk=student.pk)


class MyExamsView(APIView):
    """Parents (?student=) and students: date sheets of announced exams in the current session."""

    required_feature = Feature.EXAMS

    def get_permissions(self):
        return [HasRole.for_roles(Role.PARENT, Role.STUDENT)(), ActiveSubscription(), RequiresFeature()]

    def get(self, request):
        student = my_student(request)
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


