from decimal import ROUND_HALF_UP, Decimal

from .models import ExamSubject


def default_pass_marks(total, tenant):
    return (Decimal(total) * tenant.pass_percentage / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def sync_papers(exam, programs=None):
    """Add a paper for every active subject of the exam's programs that does not have one yet."""
    programs = list(programs if programs is not None else exam.programs.all())
    existing = set(ExamSubject.objects.filter(exam=exam).values_list("program_id", "subject_id"))
    new = []
    for program in programs:
        for subject in program.subjects.filter(is_active=True):
            if (program.id, subject.id) not in existing:
                new.append(
                    ExamSubject(
                        tenant=exam.tenant, exam=exam, program=program, subject=subject,
                        total_marks=Decimal(100), pass_marks=default_pass_marks(100, exam.tenant),
                    )
                )
    ExamSubject.objects.bulk_create(new)
    return len(new)
