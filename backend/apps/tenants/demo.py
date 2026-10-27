"""A small, realistic demo institute for showing the system to clients.

``wipe_institutes`` deletes institutes with all their data (platform super admins and plans stay);
``seed_demo`` builds "Bright Future Academy" (code ``demo``) with students, attendance, fees and exams.
Random values come from a fixed seed, so every run gives the same school.
"""

import datetime
import random
from decimal import ROUND_HALF_UP, Decimal

from django.apps import apps
from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.academics.models import AcademicSession, Program, Section, Subject
from apps.accounts.models import Role, User
from apps.attendance.models import AttendanceRecord, AttendanceStatus
from apps.core.timeutils import tenant_today
from apps.exams.models import Exam, ExamStatus, ExamSubject, Mark
from apps.exams.services import default_pass_marks, sync_papers
from apps.fees.models import DiscountType, FeeHead, FeeRate, Frequency, Invoice, PaymentMethod, StudentDiscount
from apps.fees.services import generate_monthly_invoices, record_payment
from apps.students.models import Enrollment, Guardian, Relation, Student, StudentGuardian
from apps.subscriptions.models import BillingCycle, Plan, Subscription, SubscriptionStatus

from .models import Tenant

DEMO_CODE = "demo"
DEMO_PASSWORD = "demo1234"

BOYS = ["Ahmed", "Hamza", "Usman", "Bilal", "Hassan", "Ali", "Zain", "Saad", "Daniyal", "Abdullah",
        "Haris", "Ibrahim", "Rayyan", "Taha", "Shayan", "Arham", "Musa", "Faizan"]
GIRLS = ["Fatima", "Ayesha", "Zainab", "Maryam", "Hira", "Sana", "Alishba", "Areeba", "Eman", "Hania",
         "Mahnoor", "Iqra", "Noor", "Khadija", "Laiba", "Anaya", "Rida", "Minahil"]
FAMILIES = ["Khan", "Malik", "Qureshi", "Sheikh", "Butt", "Chaudhry", "Raza", "Siddiqui", "Hussain", "Javed",
            "Iqbal", "Mirza", "Abbasi", "Awan", "Rana", "Hashmi", "Ansari", "Baig"]
FATHERS = ["Imran", "Kashif", "Asif", "Tariq", "Nadeem", "Shahid", "Faisal", "Waqas", "Adnan", "Khalid",
           "Naveed", "Sajid", "Amir", "Junaid", "Zahid", "Arif", "Shoaib", "Yasir"]

# (class, monthly tuition, subjects)
CLASSES = [
    ("Class 3", 3500, ["English", "Urdu", "Mathematics", "Science", "Islamiat"]),
    ("Class 4", 4000, ["English", "Urdu", "Mathematics", "Science", "Islamiat", "Social Studies"]),
    ("Class 5", 4500, ["English", "Urdu", "Mathematics", "Science", "Islamiat", "Social Studies", "Computer"]),
]
# (username, first name, last name, class teacher of)
TEACHERS = [
    ("sana", "Sana", "Iqbal", ("Class 5", "A")),
    ("hina", "Hina", "Aslam", ("Class 5", "B")),
    ("usman", "Usman", "Tariq", ("Class 4", "A")),
    ("ayesha", "Ayesha", "Malik", ("Class 3", "A")),
]
SECTIONS = [("Class 3", "A"), ("Class 4", "A"), ("Class 5", "A"), ("Class 5", "B")]
STUDENTS_PER_SECTION = 8


def wipe_institutes(tenants=None):
    """Delete the given institutes (default: all) and every row that belongs to them."""
    tenants = Tenant.objects.all() if tenants is None else tenants
    tenant_ids = list(tenants.values_list("id", flat=True))
    scoped = [
        m for m in apps.get_models()
        if any(f.name == "tenant" and f.related_model is Tenant for f in m._meta.fields) and m is not User
    ]
    with transaction.atomic():
        # Rows protect each other (e.g. marks protect papers), so delete in passes until all are gone.
        while scoped:
            left = []
            for model in scoped:
                try:
                    with transaction.atomic():
                        model.objects.filter(tenant_id__in=tenant_ids).delete()
                except ProtectedError:
                    left.append(model)
            if len(left) == len(scoped):
                raise RuntimeError(f"Could not delete: {[m.__name__ for m in left]}")
            scoped = left
        User.objects.filter(tenant_id__in=tenant_ids).delete()
        deleted = Tenant.objects.filter(id__in=tenant_ids).delete()
    return len(tenant_ids), deleted


def school_days(start, end):
    day = start
    while day <= end:
        if day.weekday() < 5:  # Monday to Friday
            yield day
        day += datetime.timedelta(days=1)


def half(value):
    """Round to the nearest half mark."""
    return (Decimal(value) * 2).quantize(Decimal(1), rounding=ROUND_HALF_UP) / 2


@transaction.atomic
def seed_demo(today=None):
    """Create the demo institute (replacing an existing one with the same code). Returns it."""
    wipe_institutes(Tenant.objects.filter(slug=DEMO_CODE))
    rng = random.Random(2026)

    tenant = Tenant.objects.create(
        name="Bright Future Academy", slug=DEMO_CODE, institute_type="school", country="PK", currency="PKR",
        timezone="Asia/Karachi", email="info@brightfuture-demo.pk", phone="042-35761234",
        address="12-B, Main Boulevard, Gulberg III, Lahore", password_policy="easy",
    )
    now = timezone.now()
    Subscription.objects.create(
        tenant=tenant, plan=Plan.objects.get(code="pro"), status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.YEARLY, current_period_start=now, current_period_end=now + datetime.timedelta(days=365),
    )
    today = today or tenant_today(tenant)
    user = lambda username, first, last, role: User.objects.create_user(  # noqa: E731
        username=username, password=DEMO_PASSWORD, role=role, tenant=tenant, first_name=first, last_name=last,
        email=f"{username}@brightfuture-demo.pk",
    )
    admin = user("admin", "Farhan", "Ahmed", Role.ADMIN)

    # Academic setup
    year = today.year if today.month >= 4 else today.year - 1
    session = AcademicSession.objects.create(
        tenant=tenant, name=f"{year}-{str(year + 1)[2:]}", start_date=datetime.date(year, 4, 1),
        end_date=datetime.date(year + 1, 3, 31), is_current=True,
    )
    subjects = {}
    for name in ["English", "Urdu", "Mathematics", "Science", "Islamiat", "Social Studies", "Computer"]:
        subjects[name] = Subject.objects.create(tenant=tenant, name=name)
    programs = {}
    for order, (name, _fee, subject_names) in enumerate(CLASSES, start=1):
        programs[name] = Program.objects.create(tenant=tenant, name=name, sort_order=order)
        programs[name].subjects.set([subjects[s] for s in subject_names])
    teachers = {}
    for username, first, last, (cls, sec) in TEACHERS:
        teachers[(cls, sec)] = user(username, first, last, Role.TEACHER)
    sections = {
        key: Section.objects.create(
            tenant=tenant, program=programs[key[0]], session=session, name=key[1], capacity=30, class_teacher=teachers.get(key)
        )
        for key in SECTIONS
    }

    # Students and guardians (one family has two children, with parent and student logins)
    boys, girls, families, fathers = BOYS[:], GIRLS[:], FAMILIES[:], FATHERS[:]
    for pool in (boys, girls, families, fathers):
        rng.shuffle(pool)
    ability = {}
    seq = 0

    def admit(first, last, gender, section, roll, guardian, birth_year):
        nonlocal seq
        seq += 1
        student = Student.objects.create(
            tenant=tenant, admission_no=str(seq), admission_seq=seq, first_name=first, last_name=last, gender=gender,
            date_of_birth=datetime.date(birth_year, rng.randint(1, 12), rng.randint(1, 28)),
            admission_date=datetime.date(year - rng.choice([0, 0, 1, 2, 3]), 4, rng.randint(1, 15)),
            address=guardian.address, blood_group=rng.choice(["A+", "B+", "O+", "AB+", "B-", "O-"]),
        )
        StudentGuardian.objects.create(student=student, guardian=guardian, relation=Relation.FATHER, is_primary=True)
        Enrollment.objects.create(tenant=tenant, student=student, section=section, session=session, roll_number=str(roll))
        ability[student.id] = min(max(rng.gauss(72, 13), 25), 98)
        return student

    def new_guardian(father, family, area):
        return Guardian.objects.create(
            tenant=tenant, name=f"{father} {family}", phone=f"03{rng.randint(0, 4)}{rng.randint(0, 9)}-{rng.randint(1000000, 9999999)}",
            cnic=f"35202-{rng.randint(1000000, 9999999)}-{rng.randint(1, 9)}", occupation=rng.choice(
                ["Business", "Engineer", "Doctor", "Teacher", "Banker", "Shopkeeper", "Government service", "Accountant"]
            ), address=f"House {rng.randint(1, 300)}, {area}, Lahore",
        )

    areas = ["Gulberg", "Model Town", "Johar Town", "Garden Town", "Faisal Town", "Iqbal Town", "DHA Phase 5", "Township"]
    rashid = new_guardian("Rashid", "Mehmood", "Model Town")
    rashid.user = user("rashid", "Rashid", "Mehmood", Role.PARENT)
    rashid.phone = "0300-1234567"
    rashid.save()
    birth = {"Class 3": year - 8, "Class 4": year - 9, "Class 5": year - 10}
    showcase = {}
    for key, section in sections.items():
        cls = key[0]
        roll = 1
        if key == ("Class 5", "A"):
            showcase["ahmed"] = admit("Ahmed", "Rashid", "male", section, roll, rashid, birth[cls])
            roll += 1
        if key == ("Class 3", "A"):
            showcase["fatima"] = admit("Fatima", "Rashid", "female", section, roll, rashid, birth[cls])
            roll += 1
        while roll <= STUDENTS_PER_SECTION:
            girl = roll % 2 == 0
            first = (girls if girl else boys).pop()
            father, family = fathers.pop(), families.pop()
            if not fathers:
                fathers, families = FATHERS[:], FAMILIES[:]
                rng.shuffle(fathers)
                rng.shuffle(families)
            admit(first, family, "female" if girl else "male", section, roll,
                  new_guardian(father, family, rng.choice(areas)), birth[cls])
            roll += 1
    ahmed = showcase["ahmed"]
    ahmed.user = user("ahmed", "Ahmed", "Rashid", Role.STUDENT)
    ahmed.save()
    ability[ahmed.id], ability[showcase["fatima"].id] = 88, 81
    enrollments = list(Enrollment.objects.filter(tenant=tenant).select_related("student", "section"))

    # Attendance: school days from 1 September to today. Two students attend poorly.
    regular = {e.student_id: rng.uniform(0.9, 0.99) for e in enrollments}
    showcase_ids = {ahmed.id, showcase["fatima"].id}
    for e in rng.sample([e for e in enrollments if e.student_id not in showcase_ids], 2):
        regular[e.student_id] = 0.68
    for sid in showcase_ids:
        regular[sid] = 0.985
    marked_today = {sections[("Class 5", "A")].id, sections[("Class 4", "A")].id, sections[("Class 3", "A")].id}
    records = []
    for day in school_days(max(session.start_date, datetime.date(today.year, 9, 1)), today):
        for e in enrollments:
            if day == today and e.section_id not in marked_today:
                continue
            r = 0 if day == today and e.student_id in showcase_ids else rng.random()
            if r < regular[e.student_id] - 0.04:
                status = AttendanceStatus.PRESENT
            elif r < regular[e.student_id]:
                status = AttendanceStatus.LATE
            elif r < regular[e.student_id] + 0.02:
                status = AttendanceStatus.LEAVE
            else:
                status = AttendanceStatus.ABSENT
            records.append(AttendanceRecord(
                tenant=tenant, student_id=e.student_id, section_id=e.section_id, date=day, status=status,
                marked_by=e.section.class_teacher or admin,
            ))
    AttendanceRecord.objects.bulk_create(records)

    # Fees: monthly tuition for the last six months, mostly paid; this month partly paid.
    tuition = FeeHead.objects.create(tenant=tenant, name="Tuition Fee", frequency=Frequency.MONTHLY, sort_order=1)
    exam_fee = FeeHead.objects.create(tenant=tenant, name="Annual Exam & Stationery", frequency=Frequency.ONE_TIME, sort_order=2)
    for name, fee, _subjects in CLASSES:
        FeeRate.objects.create(tenant=tenant, program=programs[name], session=session, fee_head=tuition, amount=fee)
        FeeRate.objects.create(tenant=tenant, program=programs[name], session=session, fee_head=exam_fee, amount=2000)
    StudentDiscount.objects.create(
        tenant=tenant, student=showcase["fatima"], fee_head=tuition, discount_type=DiscountType.PERCENT, value=10,
        reason="Sibling discount",
    )
    months = []
    y, m = today.year, today.month
    for _ in range(6):
        months.append((y, m))
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    late_payers = {e.student_id for e in rng.sample([e for e in enrollments if e.student_id not in showcase_ids], 4)}
    for y, m in reversed(months):
        period = f"{y}-{m:02d}"
        issue, due = datetime.date(y, m, 1), datetime.date(y, m, 10)
        generate_monthly_invoices(tenant, session, period, issue, due, user=admin)
        current = (y, m) == (today.year, today.month)
        for invoice in Invoice.objects.filter(tenant=tenant, period=period).select_related("student"):
            sid = invoice.student_id
            if sid == showcase["fatima"].id and current:
                continue  # Rashid's daughter: this month still due, to show online payment
            if current and sid != ahmed.id and rng.random() < 0.35:
                continue
            if sid in late_payers and (y, m) in months[:2]:
                if rng.random() < 0.5:
                    record_payment(invoice, (invoice.total / 2).quantize(Decimal(1)), issue + datetime.timedelta(days=12), PaymentMethod.CASH, user=admin)
                continue
            paid_on = min(issue + datetime.timedelta(days=rng.randint(1, 14)), today)
            method = rng.choices(
                [PaymentMethod.CASH, PaymentMethod.BANK, PaymentMethod.JAZZCASH, PaymentMethod.EASYPAISA], weights=[6, 2, 1, 1]
            )[0]
            reference = "" if method == PaymentMethod.CASH else f"TXN{rng.randint(100000, 999999)}"
            record_payment(invoice, invoice.total, paid_on, method, reference=reference, user=admin)

    # Exams: a published first term, an October test with marks being entered, and a mid-term being prepared.
    def make_exam(name, exam_type, start, status, total):
        exam = Exam.objects.create(
            tenant=tenant, session=session, name=name, exam_type=exam_type, start_date=start, status=status,
        )
        exam.programs.set(programs.values())
        sync_papers(exam)
        days = list(school_days(start, start + datetime.timedelta(days=20)))
        for program in programs.values():
            for i, paper in enumerate(ExamSubject.objects.filter(exam=exam, program=program).order_by("subject__name")):
                paper.total_marks = total
                paper.pass_marks = default_pass_marks(total, tenant)
                paper.date = days[i]
                paper.start_time = datetime.time(8, 30)
                paper.save()
        exam.end_date = max(p.date for p in exam.papers.all())
        exam.save()
        return exam

    def fill_marks(exam, sections_filter=None, paper_filter=None):
        marks = []
        for e in enrollments:
            if sections_filter and e.section_id not in sections_filter:
                continue
            for paper in ExamSubject.objects.filter(exam=exam, program_id=e.section.program_id).select_related("subject"):
                if paper_filter and paper.subject.name not in paper_filter:
                    continue
                if rng.random() < 0.01:
                    marks.append(Mark(tenant=tenant, paper=paper, student_id=e.student_id, section_id=e.section_id,
                                      is_absent=True, entered_by=admin))
                    continue
                pct = min(max(ability[e.student_id] + rng.gauss(0, 9), 12), 100)
                marks.append(Mark(
                    tenant=tenant, paper=paper, student_id=e.student_id, section_id=e.section_id,
                    marks_obtained=half(pct * float(paper.total_marks) / 100), entered_by=e.section.class_teacher or admin,
                ))
        Mark.objects.bulk_create(marks)

    first_term = make_exam("First Term", "term", datetime.date(year, 9, 15), ExamStatus.PUBLISHED, 100)
    fill_marks(first_term)
    october = make_exam("October Test", "test", datetime.date(year, 10, 19), ExamStatus.MARKS_OPEN, 25)
    fill_marks(october, {sections[("Class 5", "A")].id, sections[("Class 3", "A")].id})
    fill_marks(october, {sections[("Class 4", "A")].id}, {"English", "Mathematics", "Urdu"})
    make_exam("Mid-Term", "midterm", datetime.date(year, 12, 7), ExamStatus.DRAFT, 100)
    return tenant
