"""`ops` area views that are not owned by another app."""

from __future__ import annotations

from rest_framework.response import Response

from apps.accounts.permissions import IsOpsLead
from apps.common.views import ApiView
from apps.queue import selectors


class LiveView(ApiView):
    permission_classes = [IsOpsLead]

    def get(self, request, **kwargs):
        data = selectors.live_overview()
        return Response({"data": data, "count": len(data), "total": len(data)})
