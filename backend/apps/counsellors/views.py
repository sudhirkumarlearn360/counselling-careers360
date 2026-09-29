"""`ops` counsellor/posting endpoints (CQ-9/11) and the `desk/duty` state store (CQ-37)."""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.accounts.desk_context import AsCounsellorMixin
from apps.accounts.permissions import IsOpsLead, RoleIn
from apps.common.views import ApiView
from apps.counsellors import selectors, services
from apps.counsellors.serializers import CounsellorInputSerializer, DutySerializer, PostingInputSerializer


def _counsellor_or_404(counsellor_id):
    counsellor = selectors.counsellor_by_id(counsellor_id)
    if counsellor is None:
        raise NotFound()
    return counsellor


def _payload(counsellor_id) -> dict:
    return selectors.counsellor_payload(_counsellor_or_404(counsellor_id))


def _posting_payload(posting_id) -> dict:
    return selectors.posting_payload(selectors.posting_by_id(posting_id))


class CounsellorsView(ApiView):
    permission_classes = [IsOpsLead]

    def get(self, request, **kwargs):
        items = selectors.counsellor_list()
        return Response({"data": items, "count": len(items), "total": len(items)})

    def post(self, request, **kwargs):
        s = CounsellorInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        counsellor, warnings = services.create_counsellor(s.validated_data, request.user)
        return Response(
            {"data": _payload(counsellor.id), "warnings": warnings}, status=status.HTTP_201_CREATED
        )


class CounsellorDetailView(ApiView):
    permission_classes = [IsOpsLead]

    def get(self, request, counsellor_id, **kwargs):
        return Response({"data": _payload(counsellor_id)})

    def patch(self, request, counsellor_id, **kwargs):
        counsellor = _counsellor_or_404(counsellor_id)
        s = CounsellorInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        services.update_counsellor(counsellor, s.validated_data, request.user)
        return Response({"data": _payload(counsellor_id)})


class CounsellorPostingsView(ApiView):
    permission_classes = [IsOpsLead]

    def get(self, request, counsellor_id, **kwargs):
        items = _payload(counsellor_id)["postings"]
        return Response({"data": items, "count": len(items), "total": len(items)})

    def post(self, request, counsellor_id, **kwargs):
        counsellor = _counsellor_or_404(counsellor_id)
        s = PostingInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        posting, warnings = services.create_posting(
            counsellor,
            s.validated_data.get("centre_id"),
            s.validated_data.get("desk_label", ""),
            request.user,
        )
        return Response(
            {"data": _posting_payload(posting.id), "warnings": warnings}, status=status.HTTP_201_CREATED
        )


class PostingDetailView(ApiView):
    permission_classes = [IsOpsLead]

    def patch(self, request, posting_id, **kwargs):
        posting = selectors.posting_by_id(posting_id)
        if posting is None:
            raise NotFound()
        s = PostingInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        _, warnings = services.update_posting(posting, s.validated_data, request.user)
        return Response({"data": _posting_payload(posting_id), "warnings": warnings})


class DutyView(AsCounsellorMixin, ApiView):
    permission_classes = [RoleIn("counsellor", "ops_lead")]

    def post(self, request, **kwargs):
        s = DutySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        posting = services.set_own_duty(
            self.desk_counsellor, s.validated_data.get("duty"), request.user, self.on_behalf_of
        )
        return Response({"data": _posting_payload(posting.id)})
