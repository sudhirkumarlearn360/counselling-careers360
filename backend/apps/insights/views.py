"""`ops` records, export and insights endpoints (ops_lead only)."""

from __future__ import annotations

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.accounts.permissions import IsOpsLead
from apps.centres.models import Centre
from apps.common.views import ApiView
from apps.insights import export, selectors


def _params(request) -> dict:
    return {k: v for k, v in request.query_params.items() if v not in ("", None)}


class OpsStudentsView(ApiView):
    permission_classes = [IsOpsLead]

    def get(self, request, **kwargs):
        rows, matched, total = selectors.student_list(_params(request))
        return Response({"data": rows, "count": matched, "total": total})


class OpsStudentsExportView(ApiView):
    permission_classes = [IsOpsLead]

    def get(self, request, **kwargs):
        params = _params(request)
        students = selectors.students_qs(params).order_by("-checkin_at", "-id")
        centre = Centre.objects.filter(pk=params["centre"]).first() if params.get("centre") else None
        body = export.build_csv(students)
        export.audit_export(students, request.user, params, students.count())
        response = HttpResponse(body, content_type="text/csv; charset=utf-8")
        name = export.filename(centre, timezone.localdate())
        response["Content-Disposition"] = f'attachment; filename="{name}"'
        return response


class OpsInsightsView(ApiView):
    permission_classes = [IsOpsLead]

    def get(self, request, **kwargs):
        centre = None
        if request.query_params.get("centre"):
            centre = (
                Centre.objects.select_related("settings").filter(pk=request.query_params["centre"]).first()
            )
            if centre is None:
                raise NotFound()
        return Response({"data": selectors.insights(centre)})
