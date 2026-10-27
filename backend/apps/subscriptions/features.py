from django.db import models


class Feature(models.TextChoices):
    """Modules a plan can include. Add new modules here as they are built."""

    ACADEMICS = "academics", "Classes, batches & subjects"
    STUDENTS = "students", "Student admission & profiles"
    ATTENDANCE = "attendance", "Attendance"
    FEES = "fees", "Fees & invoices"
    ONLINE_PAYMENTS = "online_payments", "Online fee payments"
    EXAMS = "exams", "Exams, marks & report cards"
    TIMETABLE = "timetable", "Timetable"
    HOMEWORK = "homework", "Homework & diary"
    PAYROLL = "payroll", "Staff & payroll"
    CERTIFICATES = "certificates", "Certificates"
    REPORTS = "reports", "Reports & analytics"
    SMS_ALERTS = "sms_alerts", "SMS / WhatsApp / Email alerts"
    WHITE_LABEL = "white_label", "White-labeling"
