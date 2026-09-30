"""`ops` centre endpoints (CQ-6/7/8/10). Thin: parse, call one service, shape the response."""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.accounts.permissions import IsOpsLead
from apps.centres import selectors, services
from apps.centres.models import Centre
from apps.centres.serializers import CentreInputSerializer, ConfirmSerializer
from apps.common.views import ApiView


def _centre_or_404(centre_id) -> Centre:
    centre = selectors.centre_by_id(centre_id)
    if centre is None:
        raise NotFound()
    return centre


def _payload(centre_id) -> dict:
    return selectors.centre_full_payload(_centre_or_404(centre_id))


def _confirm(request) -> bool:
    s = ConfirmSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    return s.validated_data["confirm"]


class CentresView(ApiView):
    permission_classes = [IsOpsLead]

    def get(self, request, **kwargs):
        items, total = selectors.centre_list(request.query_params.get("status") or None)
        return Response({"data": items, "count": len(items), "total": total})

    def post(self, request, **kwargs):
        s = CentreInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        centre, warnings = services.create_centre(s.validated_data, request.user)
        return Response({"data": _payload(centre.id), "warnings": warnings}, status=status.HTTP_201_CREATED)


class CentreDetailView(ApiView):
    permission_classes = [IsOpsLead]

    def get(self, request, centre_id, **kwargs):
        return Response({"data": _payload(centre_id)})

    def patch(self, request, centre_id, **kwargs):
        centre = _centre_or_404(centre_id)
        s = CentreInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        _, warnings = services.update_centre(centre, s.validated_data, request.user)
        return Response({"data": _payload(centre_id), "warnings": warnings})


class CentreGoLiveView(ApiView):
    permission_classes = [IsOpsLead]

    def post(self, request, centre_id, **kwargs):
        centre = _centre_or_404(centre_id)
        services.go_live(centre, request.user, confirm=_confirm(request))
        return Response({"data": _payload(centre_id)})


class CentreCloseView(ApiView):
    permission_classes = [IsOpsLead]

    def get(self, request, centre_id, **kwargs):
        return Response({"data": services.close_preview(_centre_or_404(centre_id))})

    def post(self, request, centre_id, **kwargs):
        centre = _centre_or_404(centre_id)
        result = services.close(centre, request.user, confirm=_confirm(request))
        return Response({"data": {**result, "centre": _payload(centre_id)}})
