"""The `as_counsellor` desk context (CQ-5), reused by every `desk/` view.

A counsellor works their own desk. An ops lead works a counsellor's desk by passing
`?as_counsellor=<counsellor_id>`; the view then knows whose desk it is (`desk_counsellor`) and who
the audit trail should say it was done on behalf of (`on_behalf_of`, None for a counsellor's own work).
Services take `actor=request.user` and `on_behalf_of=self.on_behalf_of`; notes are authored as
`desk_counsellor`.
"""

from __future__ import annotations

from rest_framework.exceptions import NotFound, PermissionDenied

from apps.accounts.models import Role
from apps.accounts.permissions import ROLE_NOT_ALLOWED_CODE, ROLE_NOT_ALLOWED_MESSAGE
from apps.common.exceptions import DomainError
from apps.counsellors.models import Counsellor

AS_COUNSELLOR_PARAM = "as_counsellor"


class AsCounsellorForbidden(PermissionDenied):
    default_code = "as_counsellor_forbidden"
    default_detail = "Only an ops lead can open another counsellor's desk."


class AsCounsellorRequired(DomainError):
    code = "as_counsellor_required"
    message = "Choose a counsellor's desk to open."


class AsCounsellorMixin:
    """Put before ApiView: `class QueueView(AsCounsellorMixin, ApiView)`, and set
    `permission_classes = [RoleIn("counsellor", "ops_lead")]`.

    Runs after authentication and the view's permission classes, so anonymous is 401 first.
    """

    desk_counsellor: Counsellor
    on_behalf_of = None
    acting_as_lead = False

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self._resolve_desk_context(request)

    def _resolve_desk_context(self, request):
        user = request.user
        raw = request.query_params.get(AS_COUNSELLOR_PARAM)
        if user.role == Role.COUNSELLOR:
            if user.counsellor is None:
                raise PermissionDenied(ROLE_NOT_ALLOWED_MESSAGE, code=ROLE_NOT_ALLOWED_CODE)
            if raw is not None:
                raise AsCounsellorForbidden()
            self.desk_counsellor, self.on_behalf_of, self.acting_as_lead = user.counsellor, None, False
        elif user.role == Role.OPS_LEAD:
            if raw is None or raw == "":
                raise AsCounsellorRequired()
            try:
                counsellor_id = int(raw)
            except ValueError:
                raise NotFound() from None
            counsellor = Counsellor.objects.filter(pk=counsellor_id).first()
            if counsellor is None:
                raise NotFound()
            self.desk_counsellor, self.on_behalf_of, self.acting_as_lead = counsellor, counsellor, True
        else:
            raise PermissionDenied(ROLE_NOT_ALLOWED_MESSAGE, code=ROLE_NOT_ALLOWED_CODE)
