from django.contrib import admin

from .models import Exam, ExamSubject, GradeBand

admin.site.register([Exam, ExamSubject, GradeBand])
