import re

from django.http import HttpResponse
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.core.permissions import HasRole
from apps.subscriptions.features import Feature
from apps.subscriptions.gating import ActiveSubscription, PaymentRequired, RequiresFeature

from .builders import REPORTS, to_json
from .excel import workbook


class ReportView(APIView):
    """GET /api/reports/<name>/?...filters  (JSON preview), add &download=xlsx for an Excel file."""

    required_feature = Feature.REPORTS

    def get_permissions(self):
        return [HasRole.for_roles(Role.ADMIN)(), ActiveSubscription(), RequiresFeature()]

    def get(self, request, name):
        if name not in REPORTS:
            raise NotFound("Unknown report.")
        builder, feature = REPORTS[name]
        tenant = request.user.tenant
        if feature not in tenant.subscription.plan.features:
            raise PaymentRequired("Your plan does not include this module.")
        report = builder(tenant, request.query_params)
        if request.query_params.get("download") == "xlsx":
            filename = re.sub(r"[^A-Za-z0-9]+", "-", report["title"]).strip("-").lower() or "report"
            response = HttpResponse(
                workbook(tenant, report), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
            return response
        return Response({
            "title": report["title"],
            "columns": [{"label": label, "kind": kind} for label, kind in report["columns"]],
            "rows": [[to_json(v) for v in row] for row in report["rows"]],
            "totals": report["totals"],
        })
