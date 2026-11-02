"""A small, realistic demo institute for showing the system to clients.

``wipe_institutes`` deletes institutes with all their data (platform super admins and plans stay);
``seed_school`` builds a complete demo school from a spec: ``DEMO`` is "Bright Future Academy" (code ``demo``),
``SCHOLARS`` is "Little Scholars School" (code ``scholars``, Nursery to Class 3 with student photos).
Random values come from a fixed seed, so every run gives the same school.
"""

import base64
import datetime
import random
import struct
import zlib
from pathlib import Path
from decimal import ROUND_HALF_UP, Decimal

from django.apps import apps
from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.academics.models import AcademicSession, Program, Section, Subject
from apps.accounts.models import Role, User
from apps.agreements.models import Kind, SignedAgreement
from apps.agreements.models import Status as AgreementStatus
from apps.agreements.services import subscription_document
from apps.attendance.models import AttendanceRecord, AttendanceStatus
from apps.core.timeutils import tenant_today
from apps.exams.models import CombinedExam, CombinedResult, Exam, ExamStatus, ExamSubject, Mark
from apps.exams.services import default_pass_marks, sync_papers
from apps.fees.models import DiscountType, FeeHead, FeeRate, Frequency, Invoice, PaymentMethod, StudentDiscount
from apps.fees.services import generate_monthly_invoices, record_payment
from apps.homework.models import Homework
from apps.payroll.models import Employee, Payslip
from apps.timetable.models import Period, TimetableEntry
from apps.students.models import Enrollment, Guardian, Relation, Student, StudentGuardian
from apps.subscriptions.models import BillingCycle, Plan, Subscription, SubscriptionStatus

from .models import Tenant

DEMO_CODE = "demo"
DEMO_PASSWORD = "demo1234"
PHOTO_DIR = Path(__file__).resolve().parent / "demo_photos"

BOYS = ["Ahmed", "Hamza", "Usman", "Bilal", "Hassan", "Ali", "Zain", "Saad", "Daniyal", "Abdullah",
        "Haris", "Ibrahim", "Rayyan", "Taha", "Shayan", "Arham", "Musa", "Faizan"]
GIRLS = ["Fatima", "Ayesha", "Zainab", "Maryam", "Hira", "Sana", "Alishba", "Areeba", "Eman", "Hania",
         "Mahnoor", "Iqra", "Noor", "Khadija", "Laiba", "Anaya", "Rida", "Minahil"]
FAMILIES = ["Khan", "Malik", "Qureshi", "Sheikh", "Butt", "Chaudhry", "Raza", "Siddiqui", "Hussain", "Javed",
            "Iqbal", "Mirza", "Abbasi", "Awan", "Rana", "Hashmi", "Ansari", "Baig"]
FATHERS = ["Imran", "Kashif", "Asif", "Tariq", "Nadeem", "Shahid", "Faisal", "Waqas", "Adnan", "Khalid",
           "Naveed", "Sajid", "Amir", "Junaid", "Zahid", "Arif", "Shoaib", "Yasir"]
OCCUPATIONS = ["Business", "Engineer", "Doctor", "Teacher", "Banker", "Shopkeeper", "Government service", "Accountant"]
TASKS = {
    "English": ["Learn the spellings of lesson 6", "Write 10 sentences using adjectives", "Read the story 'The Honest Woodcutter'"],
    "Urdu": ["سبق نمبر 5 کے سوالات کے جوابات لکھیں", "خوشخطی کا ایک صفحہ لکھیں", "مضمون: میرا پسندیدہ کھیل"],
    "Mathematics": ["Exercise 4.2, questions 1-10", "Learn the table of 13 and 14", "Solve the word problems on page 58"],
    "Science": ["Draw and label the parts of a plant", "Read chapter 3: Matter", "Write 5 sources of light"],
    "Islamiat": ["Memorise Surah Al-Asr with translation", "Write the five pillars of Islam"],
    "Social Studies": ["Locate the provinces of Pakistan on the map", "Answer questions 1-4 of chapter 2"],
    "Computer": ["Label the parts of a computer", "Write 5 uses of the internet"],
}

# The demo school ("Bright Future Academy", code ``demo``).
# classes: (class, monthly tuition, subjects, age in years at the session start)
# sections: (class, section, class teacher (username, first, last) or None, number of students)
# showcase: one parent login with two children (first name, gender, section, ability); "login" gives the
# child a student login, "discount" gives a sibling discount and leaves this month's fee unpaid.
DEMO = {
    "code": DEMO_CODE, "name": "Bright Future Academy", "legal_name": "Bright Future Academy (Pvt) Ltd",
    "email": "info@brightfuture-demo.pk", "domain": "brightfuture-demo.pk", "phone": "042-35761234",
    "address": "12-B, Main Boulevard, Gulberg III, Lahore", "city": "Lahore", "cnic": "35202",
    "brand_color": "blue", "logo": ((29, 78, 216), (234, 179, 8)),
    "principal": ("Farhan", "Ahmed", "35202-1234567-1"),
    "classes": [
        ("Class 3", 3500, ["English", "Urdu", "Mathematics", "Science", "Islamiat"], 8),
        ("Class 4", 4000, ["English", "Urdu", "Mathematics", "Science", "Islamiat", "Social Studies"], 9),
        ("Class 5", 4500, ["English", "Urdu", "Mathematics", "Science", "Islamiat", "Social Studies", "Computer"], 10),
    ],
    "subjects": ["English", "Urdu", "Mathematics", "Science", "Islamiat", "Social Studies", "Computer"],
    "sections": [
        ("Class 3", "A", ("ayesha", "Ayesha", "Malik"), 8), ("Class 4", "A", ("usman", "Usman", "Tariq"), 8),
        ("Class 5", "A", ("sana", "Sana", "Iqbal"), 8), ("Class 5", "B", ("hina", "Hina", "Aslam"), 8),
    ],
    "teacher_order": ["sana", "hina", "usman", "ayesha"], "teacher_pay": (42000, 3000, 5000),
    "parent": ("rashid", "Rashid", "Mehmood", "0300-1234567", "Model Town"), "children_last_name": "Rashid",
    "children": [
        {"first": "Ahmed", "gender": "male", "section": ("Class 5", "A"), "ability": 88, "login": "ahmed"},
        {"first": "Fatima", "gender": "female", "section": ("Class 3", "A"), "ability": 81, "discount": True},
    ],
    "boys": BOYS, "girls": GIRLS, "families": FAMILIES, "fathers": FATHERS, "occupations": OCCUPATIONS,
    "areas": ["Gulberg", "Model Town", "Johar Town", "Garden Town", "Faisal Town", "Iqbal Town", "DHA Phase 5", "Township"],
    "poor_attendance": 2, "late_payers": 4, "not_marked_today": [("Class 5", "B")],
    "october_full": [("Class 5", "A"), ("Class 3", "A")], "october_partial": [("Class 4", "A")],
    "staff": [("Muhammad Akram", "Security guard", 28000, 2000), ("Shahid Masih", "Office assistant", 30000, 2000),
              ("Bashir Ahmed", "Van driver", 32000, 3000)],
    "tasks": TASKS, "photos": False,
    "applications": [
        ("Hania", "Qureshi", "female", (2, 14), "Kamran Qureshi", "0301-5550101", "father", "Gulberg, Lahore", "Looking for a seat this term."),
        ("Musa", "Siddiqui", "male", (9, 2), "Nadia Siddiqui", "0333-5550202", "mother", "Gulberg, Lahore", ""),
    ],
}

# A primary school from Nursery to Class 3 (two sections each, about 20 students per section) with an
# illustrated, age-matched photo for every student. Code ``scholars``.
SCHOLARS_CODE = "scholars"
SCHOLARS = {
    "code": SCHOLARS_CODE, "name": "Little Scholars School", "legal_name": "Little Scholars School (Pvt) Ltd",
    "email": "info@littlescholars-demo.pk", "domain": "littlescholars-demo.pk", "phone": "021-34981234",
    "address": "Plot 47, Block 13-D, Gulshan-e-Iqbal, Karachi", "city": "Karachi", "cnic": "42201",
    "brand_color": "green", "logo": ((21, 128, 61), (250, 204, 21)),
    "principal": ("Shazia", "Kamal", "42201-7654321-2"),
    "classes": [
        ("Nursery", 2500, ["English", "Urdu", "Mathematics", "General Knowledge", "Drawing"], 4),
        ("Prep", 2800, ["English", "Urdu", "Mathematics", "General Knowledge", "Islamiat", "Drawing"], 5),
        ("Class 1", 3000, ["English", "Urdu", "Mathematics", "General Knowledge", "Islamiat", "Computer"], 6),
        ("Class 2", 3200, ["English", "Urdu", "Mathematics", "General Knowledge", "Islamiat", "Computer"], 7),
        ("Class 3", 3500, ["English", "Urdu", "Mathematics", "Science", "Social Studies", "Islamiat", "Computer"], 8),
    ],
    "subjects": ["English", "Urdu", "Mathematics", "General Knowledge", "Science", "Social Studies", "Islamiat",
                 "Computer", "Drawing"],
    "sections": [
        ("Nursery", "A", ("rabia", "Rabia", "Anwar"), 20), ("Nursery", "B", ("saima", "Saima", "Khalid"), 19),
        ("Prep", "A", ("asma", "Asma", "Rehman"), 21), ("Prep", "B", ("bushra", "Bushra", "Naeem"), 20),
        ("Class 1", "A", ("nida", "Nida", "Farooq"), 20), ("Class 1", "B", ("amna", "Amna", "Shafiq"), 21),
        ("Class 2", "A", ("farah", "Farah", "Javed"), 19), ("Class 2", "B", ("kiran", "Kiran", "Aslam"), 20),
        ("Class 3", "A", ("teacher", "Mehwish", "Ali"), 21), ("Class 3", "B", ("adeel", "Adeel", "Hassan"), 20),
    ],
    "teacher_order": ["teacher", "adeel", "kiran", "farah", "amna", "nida", "bushra", "asma", "saima", "rabia"],
    "teacher_pay": (32000, 1500, 3000),
    "parent": ("parent", "Imran", "Siddiqui", "0321-2345678", "Gulshan-e-Iqbal"), "children_last_name": "Siddiqui",
    "children": [
        {"first": "Hamza", "gender": "male", "section": ("Class 3", "A"), "ability": 87, "login": "student"},
        {"first": "Anaya", "gender": "female", "section": ("Prep", "A"), "ability": 82, "discount": True},
    ],
    "boys": ["Ahmed", "Hamza", "Usman", "Bilal", "Hassan", "Ali", "Zain", "Saad", "Daniyal", "Abdullah", "Haris",
             "Ibrahim", "Rayyan", "Taha", "Shayan", "Arham", "Musa", "Faizan", "Ayaan", "Rohaan", "Azlan", "Hadi",
             "Muhammad", "Umar", "Yusuf", "Zayan", "Aliyan", "Saim", "Huzaifa", "Moiz", "Fahad", "Sameer", "Arsalan",
             "Talha", "Sufyan", "Abdul Rehman", "Mustafa", "Raza", "Ismail", "Affan", "Wali", "Shaheer", "Mikael",
             "Rafay", "Ahad", "Subhan", "Owais", "Zohaib", "Hashir", "Uzair"],
    "girls": ["Fatima", "Ayesha", "Zainab", "Maryam", "Hira", "Sana", "Alishba", "Areeba", "Eman", "Hania",
              "Mahnoor", "Iqra", "Noor", "Khadija", "Laiba", "Rida", "Minahil", "Aiza", "Inaya", "Zoha", "Haniya",
              "Anabia", "Hoorain", "Manahil", "Dua", "Aleena", "Mishal", "Abeeha", "Mehak", "Sidra", "Javeria",
              "Barira", "Umme Hani", "Rameen", "Sakina", "Arfa", "Kinza", "Zara", "Wajiha", "Fizza", "Amna",
              "Hafsa", "Ruqayya", "Huda", "Aliza", "Mirha", "Zunaira", "Neha", "Shiza", "Emaan"],
    "families": ["Khan", "Malik", "Qureshi", "Sheikh", "Butt", "Chaudhry", "Raza", "Hussain", "Javed", "Iqbal",
                 "Mirza", "Abbasi", "Awan", "Rana", "Hashmi", "Ansari", "Baig", "Memon", "Shah", "Zaidi", "Rizvi",
                 "Naqvi", "Jafri", "Usmani", "Farooqui", "Lodhi", "Niazi", "Soomro", "Baloch", "Pathan", "Ghouri",
                 "Kazmi", "Bukhari", "Saeed", "Aziz", "Haider", "Akhtar", "Khattak", "Durrani", "Kamal"],
    "fathers": ["Kashif", "Asif", "Tariq", "Nadeem", "Shahid", "Faisal", "Waqas", "Adnan", "Khalid", "Naveed",
                "Sajid", "Amir", "Junaid", "Zahid", "Arif", "Shoaib", "Yasir", "Rizwan", "Salman", "Farhan", "Atif",
                "Bilal", "Jawad", "Kamran", "Mohsin", "Noman", "Owais", "Qasim", "Rehan", "Sohail", "Tahir", "Umair",
                "Wasim", "Zeeshan", "Fahim", "Hammad", "Irfan", "Majid", "Saqib", "Talha"],
    "occupations": OCCUPATIONS + ["Software engineer", "Pharmacist", "Army officer", "Trader", "Sales manager", "Lawyer"],
    "areas": ["Gulshan-e-Iqbal", "Gulistan-e-Johar", "PECHS", "North Nazimabad", "Clifton", "DHA Phase 6",
              "Federal B Area", "Bahadurabad", "Tariq Road", "Malir Cantt"],
    "poor_attendance": 5, "late_payers": 12, "not_marked_today": [("Class 3", "B"), ("Nursery", "B")],
    "october_full": [("Class 3", "A"), ("Class 2", "A"), ("Class 1", "A"), ("Prep", "A"), ("Nursery", "A")],
    "october_partial": [("Class 3", "B"), ("Class 2", "B")],
    "staff": [("Ghulam Rasool", "Security guard", 26000, 2000), ("Parveen Bibi", "Aaya (Nursery helper)", 22000, 1500),
              ("Rukhsana Bibi", "Aaya (Prep helper)", 22000, 1500), ("Asif Masih", "Office assistant", 28000, 2000),
              ("Sher Khan", "Van driver", 30000, 3000)],
    "tasks": {
        "English": ["Write capital letters A to Z neatly", "Learn the poem 'Twinkle Twinkle Little Star'",
                    "Write 5 words that start with 'b'", "Read lesson 4 aloud at home", "Learn the spellings of colours"],
        "Urdu": ["حروفِ تہجی الف سے ے تک لکھیں", "دو حرفی الفاظ کی مشق کریں", "نظم 'مچھلی' یاد کریں", "خوشخطی کا ایک صفحہ لکھیں"],
        "Mathematics": ["Write counting 1 to 50", "Learn the table of 2", "Do the sums on page 14",
                        "Draw shapes: circle, square and triangle", "Write the missing numbers 1-100"],
        "General Knowledge": ["Name 5 fruits and colour them", "Learn the names of the days of the week",
                              "Draw your family and write their names", "Name 5 animals and their sounds"],
        "Science": ["Name the five senses", "Draw and label the parts of a plant", "Write 3 sources of water"],
        "Social Studies": ["Write the name of your city and province", "Learn about our national flag"],
        "Islamiat": ["Learn the Kalima Tayyiba", "Memorise Surah Al-Ikhlas", "Learn the dua before eating"],
        "Computer": ["Label the parts of a computer", "Draw a computer and colour it"],
        "Drawing": ["Colour the apple in your drawing book", "Draw a house and a tree", "Make a paper boat"],
    },
    "photos": True,
    # Photos the owner supplied for a few students (class, section, roll); everyone else keeps a drawing.
    "real_photos": {("Class 1", "A", 1): "real_1_b.jpg", ("Class 3", "A", 1): "real_4_b.jpg"},
    "applications": [
        ("Zoya", "Mirza", "female", (3, 9), "Babar Mirza", "0302-5550303", "father", "Gulistan-e-Johar, Karachi", "Seat required in Nursery."),
        ("Ayaan", "Memon", "male", (6, 21), "Sadia Memon", "0345-5550404", "mother", "PECHS, Karachi", ""),
    ],
}
SCHOOLS = {DEMO_CODE: DEMO, SCHOLARS_CODE: SCHOLARS}


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


def demo_logo(size=128, disc=(29, 78, 216), ring=(234, 179, 8)):
    """A simple badge logo (coloured disc, ring, white open book) as a PNG data URL."""
    c, rows = size / 2, bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            r = ((x - c) ** 2 + (y - c) ** 2) ** 0.5
            dx, dy = abs(x - c) / size, (y - c) / size
            page = 0.04 < dx < 0.30 and -0.18 + dx * 0.25 < dy < 0.16 + dx * 0.25
            if r > c - 1:
                rows += bytes((0, 0, 0, 0))
            elif r > c - 8:
                rows += bytes((*ring, 255))
            elif page:
                rows += bytes((255, 255, 255, 255))
            else:
                rows += bytes((*disc, 255))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b""))
    return "data:image/png;base64," + base64.b64encode(png).decode()


def student_photo(level, gender, number):
    """An illustrated student photo (age level 0-4, 'b'/'g') from ``demo_photos`` as a JPEG data URL."""
    files = sorted(PHOTO_DIR.glob(f"{min(level, 4)}_{gender}_*.jpg"))
    return "data:image/jpeg;base64," + base64.b64encode(files[number % len(files)].read_bytes()).decode()


class Pool:
    """Shuffled names handed out one by one; reshuffled when used up."""

    def __init__(self, rng, names):
        self.rng, self.names, self.left = rng, list(names), []

    def pop(self):
        if not self.left:
            self.left = self.names[:]
            self.rng.shuffle(self.left)
        return self.left.pop()


def seed_demo(today=None):
    """Create the demo institute "Bright Future Academy" (code ``demo``)."""
    return seed_school(DEMO, today)


@transaction.atomic
def seed_school(spec, today=None):
    """Create a demo institute from ``spec`` (replacing an existing one with the same code). Returns it."""
    code = spec["code"]
    wipe_institutes(Tenant.objects.filter(slug=code))
    rng = random.Random(2026)

    tenant = Tenant.objects.create(
        name=spec["name"], slug=code, institute_type="school", country="PK", currency="PKR",
        timezone="Asia/Karachi", email=spec["email"], phone=spec["phone"],
        address=spec["address"], password_policy="easy",
        logo=demo_logo(disc=spec["logo"][0], ring=spec["logo"][1]), brand_color=spec["brand_color"],
    )
    now = timezone.now()
    Subscription.objects.create(
        tenant=tenant, plan=Plan.objects.get(code="pro"), status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.YEARLY, current_period_start=now, current_period_end=now + datetime.timedelta(days=365),
    )
    today = today or tenant_today(tenant)
    pro = Plan.objects.get(code="pro")
    doc = subscription_document(pro, BillingCycle.YEARLY, "PKR")
    p_first, p_last, p_cnic = spec["principal"]
    SignedAgreement.objects.create(
        tenant=tenant, kind=Kind.SUBSCRIPTION, version=doc["version"], status=AgreementStatus.ACTIVE, plan=pro,
        billing_cycle=BillingCycle.YEARLY, amount=doc["amount"], currency=doc["currency"],
        institute_legal_name=spec["legal_name"], institute_address=tenant.address, signer_name=f"{p_first} {p_last}",
        signer_designation="Principal", signer_cnic=p_cnic, signer_phone=tenant.phone, signature=f"{p_first} {p_last}",
        provider=doc["provider"], schedule=doc["schedule"], sections=doc["sections"], period_start=now,
        period_end=now + datetime.timedelta(days=365), activated_at=now,
    )
    user = lambda username, first, last, role: User.objects.create_user(  # noqa: E731
        username=username, password=DEMO_PASSWORD, role=role, tenant=tenant, first_name=first, last_name=last,
        email=f"{username}@{spec['domain']}",
    )
    admin = user("admin", p_first, p_last, Role.ADMIN)

    # Academic setup
    year = today.year if today.month >= 4 else today.year - 1
    session = AcademicSession.objects.create(
        tenant=tenant, name=f"{year}-{str(year + 1)[2:]}", start_date=datetime.date(year, 4, 1),
        end_date=datetime.date(year + 1, 3, 31), is_current=True,
    )
    class_subjects = {name: subject_names for name, _fee, subject_names, _age in spec["classes"]}
    subjects = {name: Subject.objects.create(tenant=tenant, name=name) for name in spec["subjects"]}
    programs = {}
    for order, (name, _fee, subject_names, _age) in enumerate(spec["classes"], start=1):
        programs[name] = Program.objects.create(tenant=tenant, name=name, sort_order=order)
        programs[name].subjects.set([subjects[s] for s in subject_names])
    teachers = {}
    for cls, sec, teacher, _count in spec["sections"]:
        if teacher:
            teachers[(cls, sec)] = user(*teacher, Role.TEACHER)
    sections = {
        (cls, sec): Section.objects.create(
            tenant=tenant, program=programs[cls], session=session, name=sec, capacity=30, class_teacher=teachers.get((cls, sec))
        )
        for cls, sec, _teacher, _count in spec["sections"]
    }

    # Students and guardians (one family has two children, with parent and student logins)
    boys, girls = Pool(rng, spec["boys"]), Pool(rng, spec["girls"])
    fathers, families = spec["fathers"][:], spec["families"][:]
    rng.shuffle(fathers)
    rng.shuffle(families)
    ability = {}
    seq = 0
    level = {name: i for i, (name, *_rest) in enumerate(spec["classes"])}
    ages = {name: age for name, _fee, _subjects, age in spec["classes"]}
    photo_count = {}
    city = spec["city"]

    def admit(first, last, gender, section_key, roll, guardian, birth_year):
        nonlocal seq
        seq += 1
        photo = ""
        if spec["photos"]:
            key = (level[section_key[0]], "g" if gender == "female" else "b")
            photo = student_photo(key[0], key[1], photo_count.get(key, 0))
            photo_count[key] = photo_count.get(key, 0) + 1
            real = spec.get("real_photos", {}).get((*section_key, roll))
            if real:
                photo = "data:image/jpeg;base64," + base64.b64encode((PHOTO_DIR / real).read_bytes()).decode()
        student = Student.objects.create(
            tenant=tenant, admission_no=str(seq), admission_seq=seq, first_name=first, last_name=last, gender=gender,
            date_of_birth=datetime.date(birth_year, rng.randint(1, 12), rng.randint(1, 28)),
            admission_date=datetime.date(year - rng.choice([n for n in (0, 0, 1, 2, 3) if n <= ages[section_key[0]] - 4]), 4, rng.randint(1, 15)),
            address=guardian.address, blood_group=rng.choice(["A+", "B+", "O+", "AB+", "B-", "O-"]), photo=photo,
        )
        StudentGuardian.objects.create(student=student, guardian=guardian, relation=Relation.FATHER, is_primary=True)
        Enrollment.objects.create(tenant=tenant, student=student, section=sections[section_key], session=session, roll_number=str(roll))
        ability[student.id] = min(max(rng.gauss(72, 13), 25), 98)
        return student

    def new_guardian(father, family, area):
        return Guardian.objects.create(
            tenant=tenant, name=f"{father} {family}", phone=f"03{rng.randint(0, 4)}{rng.randint(0, 9)}-{rng.randint(1000000, 9999999)}",
            cnic=f"{spec['cnic']}-{rng.randint(1000000, 9999999)}-{rng.randint(1, 9)}", occupation=rng.choice(spec["occupations"]),
            address=f"House {rng.randint(1, 300)}, {area}, {city}",
        )

    p_user, p_first, p_last, p_phone, p_area = spec["parent"]
    parent = new_guardian(p_first, p_last, p_area)
    parent.user = user(p_user, p_first, p_last, Role.PARENT)
    parent.phone = p_phone
    parent.save()
    birth = {name: year - age for name, _fee, _subjects, age in spec["classes"]}
    showcase = {}
    for cls, sec, _teacher, count in spec["sections"]:
        roll = 1
        for child in spec["children"]:
            if child["section"] == (cls, sec):
                showcase[child["first"]] = admit(child["first"], spec["children_last_name"], child["gender"], (cls, sec), roll, parent, birth[cls])
                roll += 1
        while roll <= count:
            girl = roll % 2 == 0
            first = (girls if girl else boys).pop()
            father, family = fathers.pop(), families.pop()
            if not fathers:
                fathers, families = spec["fathers"][:], spec["families"][:]
                rng.shuffle(fathers)
                rng.shuffle(families)
            admit(first, family, "female" if girl else "male", (cls, sec), roll,
                  new_guardian(father, family, rng.choice(spec["areas"])), birth[cls])
            roll += 1
    login_child = discount_child = None
    for child in spec["children"]:
        student = showcase[child["first"]]
        ability[student.id] = child["ability"]
        if child.get("login"):
            login_child = student
            student.user = user(child["login"], student.first_name, student.last_name, Role.STUDENT)
            student.save()
        if child.get("discount"):
            discount_child = student
    enrollments = list(Enrollment.objects.filter(tenant=tenant).select_related("student", "section"))

    # Attendance: school days from 1 September to today. A few students attend poorly.
    regular = {e.student_id: rng.uniform(0.9, 0.99) for e in enrollments}
    showcase_ids = {s.id for s in showcase.values()}
    for e in rng.sample([e for e in enrollments if e.student_id not in showcase_ids], spec["poor_attendance"]):
        regular[e.student_id] = 0.68
    for sid in showcase_ids:
        regular[sid] = 0.985
    marked_today = {s.id for key, s in sections.items() if key not in spec["not_marked_today"]}
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
    AttendanceRecord.objects.bulk_create(records, batch_size=2000)

    # Fees: monthly tuition for the last six months, mostly paid; this month partly paid.
    tuition = FeeHead.objects.create(tenant=tenant, name="Tuition Fee", frequency=Frequency.MONTHLY, sort_order=1)
    exam_fee = FeeHead.objects.create(tenant=tenant, name="Annual Exam & Stationery", frequency=Frequency.ONE_TIME, sort_order=2)
    for name, fee, _subjects, _age in spec["classes"]:
        FeeRate.objects.create(tenant=tenant, program=programs[name], session=session, fee_head=tuition, amount=fee)
        FeeRate.objects.create(tenant=tenant, program=programs[name], session=session, fee_head=exam_fee, amount=2000)
    if discount_child:
        StudentDiscount.objects.create(
            tenant=tenant, student=discount_child, fee_head=tuition, discount_type=DiscountType.PERCENT, value=10,
            reason="Sibling discount",
        )
    months = []
    y, m = today.year, today.month
    for _ in range(6):
        months.append((y, m))
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    late_payers = {e.student_id for e in rng.sample([e for e in enrollments if e.student_id not in showcase_ids], spec["late_payers"])}
    for y, m in reversed(months):
        period = f"{y}-{m:02d}"
        issue, due = datetime.date(y, m, 1), datetime.date(y, m, 10)
        generate_monthly_invoices(tenant, session, period, issue, due, user=admin)
        current = (y, m) == (today.year, today.month)
        for invoice in Invoice.objects.filter(tenant=tenant, period=period).select_related("student"):
            sid = invoice.student_id
            if discount_child and sid == discount_child.id and current:
                continue  # the parent's younger child: this month still due, to show online payment
            if current and (not login_child or sid != login_child.id) and rng.random() < 0.35:
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
        Mark.objects.bulk_create(marks, batch_size=2000)

    first_term = make_exam("First Term", "term", datetime.date(year, 9, 15), ExamStatus.PUBLISHED, 100)
    fill_marks(first_term)
    october = make_exam("October Test", "test", datetime.date(year, 10, 19), ExamStatus.MARKS_OPEN, 25)
    fill_marks(october, {sections[key].id for key in spec["october_full"]})
    fill_marks(october, {sections[key].id for key in spec["october_partial"]}, {"English", "Mathematics", "Urdu"})
    mid_term = make_exam("Mid-Term", "midterm", datetime.date(year, 12, 7), ExamStatus.DRAFT, 100)
    final = make_exam("Final Exam", "final", datetime.date(year + 1, 3, 1), ExamStatus.DRAFT, 100)
    annual = CombinedResult.objects.create(tenant=tenant, session=session, name=f"Annual Result {session.name}")
    CombinedExam.objects.bulk_create([
        CombinedExam(combined=annual, exam=first_term, weight=25),
        CombinedExam(combined=annual, exam=mid_term, weight=25),
        CombinedExam(combined=annual, exam=final, weight=50),
    ])

    # Timetable: 7 periods with a break after the 4th; each class teacher takes their own section.
    clock = datetime.datetime(2000, 1, 1, 8, 0)
    periods = []
    for number in range(1, 8):
        end = clock + datetime.timedelta(minutes=40)
        periods.append(Period.objects.create(tenant=tenant, name=f"Period {number}", start_time=clock.time(), end_time=end.time()))
        clock = end
        if number == 4:
            end = clock + datetime.timedelta(minutes=20)
            Period.objects.create(tenant=tenant, name="Break", start_time=clock.time(), end_time=end.time(), is_break=True)
            clock = end
    rooms = {key: f"Room {i}" for i, key in enumerate(sections, start=1)}
    entries = []
    for key, section in sections.items():
        names = class_subjects[key[0]]
        for day in range(5):
            for i, period in enumerate(periods):
                entries.append(TimetableEntry(
                    tenant=tenant, section=section, day=day, period=period, subject=subjects[names[(i + day) % len(names)]],
                    teacher=teachers.get(key), room=rooms[key],
                ))
    TimetableEntry.objects.bulk_create(entries)

    # Homework diary for the last five school days.
    tasks = spec["tasks"]
    school_days_back = [d for d in (today - datetime.timedelta(days=n) for n in range(10)) if d.weekday() < 5][:5]
    diary = []
    for key, section in sections.items():
        names = class_subjects[key[0]]
        for n, day in enumerate(school_days_back):
            for subject_name in rng.sample(names, 2):
                diary.append(Homework(
                    tenant=tenant, section=section, subject=subjects[subject_name], date=day, title=rng.choice(tasks[subject_name]),
                    due_date=day + datetime.timedelta(days=1 if day.weekday() < 4 else 3), created_by=teachers.get(key) or admin,
                ))
    Homework.objects.bulk_create(diary)

    # Staff and salaries: last month paid, this month partly paid.
    base, step, extra = spec["teacher_pay"]
    by_username = {t.username: t for t in teachers.values()}
    staff = [(t.get_full_name(), "Teacher", base + step * i, extra, t)
             for i, t in enumerate(by_username[u] for u in spec["teacher_order"])]
    staff += [(name, role, basic, allowance, None) for name, role, basic, allowance in spec["staff"]]
    employees = [
        Employee.objects.create(tenant=tenant, name=name, designation=role, basic_salary=basic, allowance=allowance, user=login,
                                phone=f"03{rng.randint(0, 4)}{rng.randint(0, 9)}-{rng.randint(1000000, 9999999)}",
                                join_date=datetime.date(year - rng.randint(0, 4), rng.randint(1, 12), 1))
        for name, role, basic, allowance, login in staff
    ]
    previous = (today.replace(day=1) - datetime.timedelta(days=1))
    for period, paid_share in ((previous.strftime("%Y-%m"), 1.0), (today.strftime("%Y-%m"), 0.5)):
        for i, e in enumerate(employees):
            deduction = 1500 if i == 1 and paid_share == 1.0 else 0
            slip = Payslip.objects.create(tenant=tenant, employee=e, period=period, basic=e.basic_salary, allowance=e.allowance,
                                          deduction=deduction, note="1 day unpaid leave" if deduction else "")
            if i < len(employees) * paid_share:
                slip.status, slip.paid_on, slip.paid_by = "paid", min(datetime.date.fromisoformat(f"{period}-01") + datetime.timedelta(days=27), today), admin
                slip.method = "bank" if e.user_id else "cash"
                slip.save()

    # Parent messages: today's absent alerts and fee reminders wait in the outbox (free WhatsApp mode).
    from apps.messaging.alerts import absent_alerts, fee_reminders

    if today.weekday() < 5:
        for section in sections.values():
            if section.id in marked_today:
                records = AttendanceRecord.objects.filter(section=section, date=today).values("student", "status")
                absent_alerts(tenant, section, today, list(records), admin)
    fee_reminders(tenant, admin)

    # Online admission form is open, with two applications waiting for a decision.
    from apps.admissions.models import Application

    tenant.admissions_open = True
    tenant.save(update_fields=["admissions_open"])
    first_class, _fee, _subjects, first_age = spec["classes"][0]
    for number, (first, last, gender, (month, day), guardian, phone, relation, address, note) in enumerate(spec["applications"], start=1):
        Application.objects.create(
            tenant=tenant, number=number, first_name=first, last_name=last, gender=gender,
            date_of_birth=datetime.date(today.year - first_age, month, day), program=programs[first_class],
            guardian_name=guardian, guardian_phone=phone, guardian_relation=relation, address=address, message=note,
        )
    return tenant
