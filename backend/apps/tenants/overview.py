"""The platform owner's dashboard: institutes, plans, renewals due and subscription revenue."""

import datetime
from collections import defaultdict
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role, User
from apps.core.permissions import IsSuperAdmin
from apps.students.models import Student, StudentStatus
from apps.subscriptions.models import Subscription, SubscriptionPayment, SubscriptionStatus

from .models import Tenant

EXPIRING_DAYS = 14


def month_start(day):
    return day.replace(day=1)


def add_months(day, months):
    total = day.year * 12 + day.month - 1 + months
    return datetime.date(total // 12, total % 12 + 1, 1)


def money(value):
    return f"{Decimal(value or 0):.2f}"


def brief(sub):
    return {
        "tenant": sub.tenant_id, "name": sub.tenant.name, "slug": sub.tenant.slug, "plan": sub.plan.name,
        "status": sub.effective_status, "days_left": sub.days_left, "period_end": sub.current_period_end,
        "email": sub.tenant.email, "phone": sub.tenant.phone,
    }


class PlatformOverviewView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        zone = ZoneInfo(settings.PLATFORM_TIMEZONE)
        now = timezone.now()
        today = timezone.localdate(timezone=zone)
        this_month = month_start(today)
        start = lambda day: datetime.datetime.combine(day, datetime.time.min, tzinfo=zone)  # noqa: E731

        subs = list(Subscription.objects.select_related("tenant", "plan"))
        status_counts = defaultdict(int)
        plan_counts = defaultdict(int)
        for sub in subs:
            status_counts["suspended" if not sub.tenant.is_active else sub.effective_status] += 1
            if sub.tenant.is_active and sub.is_usable:
                plan_counts[sub.plan.name] += 1

        usable = [s for s in subs if s.tenant.is_active and s.is_usable]
        expiring = sorted((s for s in usable if s.current_period_end <= now + datetime.timedelta(days=EXPIRING_DAYS)),
                          key=lambda s: s.current_period_end)
        expired = sorted((s for s in subs if s.tenant.is_active and not s.is_usable),
                         key=lambda s: s.current_period_end, reverse=True)

        payments = SubscriptionPayment.objects.order_by()
        first_month = add_months(this_month, -5)
        monthly = defaultdict(lambda: defaultdict(Decimal))
        rows = (
            payments.filter(created_at__gte=start(first_month))
            .annotate(month=TruncMonth("created_at", tzinfo=zone))
            .values("month", "currency").annotate(total=Sum("amount"))
        )
        for row in rows:
            monthly[row["currency"]][row["month"].date().isoformat()[:7]] += row["total"]
        months = [add_months(first_month, i).isoformat()[:7] for i in range(6)]
        revenue = []
        for currency in sorted(monthly) or ["PKR"]:
            series = [money(monthly[currency][m]) for m in months]
            year_total = payments.filter(currency=currency, created_at__gte=start(datetime.date(today.year, 1, 1))).aggregate(s=Sum("amount"))["s"]
            revenue.append({"currency": currency, "this_month": series[-1], "last_month": series[-2], "this_year": money(year_total),
                            "months": [{"month": m, "amount": a} for m, a in zip(months, series)]})

        recent_payments = payments.select_related("subscription__tenant", "plan").order_by("-created_at")[:6]
        tenants = Tenant.objects.all()
        from apps.backups.views import last_backup

        return Response({
            "last_backup": last_backup(),
            "institutes": {
                "total": tenants.count(),
                "active": len(usable),
                "trial": status_counts[SubscriptionStatus.TRIALING],
                "paying": status_counts[SubscriptionStatus.ACTIVE],
                "expired": status_counts[SubscriptionStatus.EXPIRED] + status_counts[SubscriptionStatus.PAST_DUE] + status_counts[SubscriptionStatus.CANCELLED],
                "suspended": status_counts["suspended"],
                "new_this_month": tenants.filter(created_at__gte=start(this_month)).count(),
            },
            "plans": [{"plan": name, "institutes": count} for name, count in sorted(plan_counts.items(), key=lambda x: -x[1])],
            "students": Student.objects.filter(status=StudentStatus.ACTIVE, tenant__is_active=True).count(),
            "users": User.objects.exclude(role=Role.SUPER_ADMIN).filter(is_active=True).count(),
            "revenue": revenue,
            "expiring": [brief(s) for s in expiring],
            "expired": [brief(s) for s in expired[:10]],
            "recent_institutes": [
                {"id": t.id, "name": t.name, "slug": t.slug, "institute_type": t.get_institute_type_display(), "created_at": t.created_at}
                for t in tenants.order_by("-created_at")[:6]
            ],
            "recent_payments": [
                {"id": p.id, "name": p.subscription.tenant.name, "plan": p.plan.name, "amount": money(p.amount),
                 "currency": p.currency, "method": p.get_method_display(), "created_at": p.created_at}
                for p in recent_payments
            ],
            "top_institutes": list(
                Student.objects.filter(status=StudentStatus.ACTIVE, tenant__is_active=True).order_by()
                .values("tenant_id", "tenant__name").annotate(students=Count("id")).order_by("-students")[:5]
            ),
        })
