"""Role permissions. Anonymous callers get 401 (DRF), a signed-in wrong role gets 403 `role_not_allowed`."""

from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.accounts.models import Role

ROLE_NOT_ALLOWED_MESSAGE = "Your role can't open this screen."
ROLE_NOT_ALLOWED_CODE = "role_not_allowed"
_VALID_ROLES = {r.value for r in Role}


def RoleIn(*roles: str) -> type:  # noqa: N802 - used like a permission class: permission_classes = [RoleIn(...)]
    """Build a permission class that allows only signed-in, active users whose role is in `roles`."""
    allowed = frozenset(str(r) for r in roles)
    unknown = allowed - _VALID_ROLES
    if not allowed or unknown:
        raise ValueError(f"Unknown or empty role list: {sorted(unknown) or roles}")

    class _RoleIn(BasePermission):
        message = ROLE_NOT_ALLOWED_MESSAGE
        code = ROLE_NOT_ALLOWED_CODE
        allowed_roles = allowed

        def has_permission(self, request, view):
            user = request.user
            return bool(user and user.is_authenticated and user.is_active and user.role in self.allowed_roles)

    _RoleIn.__name__ = "RoleIn_" + "_".join(sorted(allowed))
    return _RoleIn


IsOpsLead = RoleIn(Role.OPS_LEAD)
IsReception = RoleIn(Role.RECEPTION)
IsCounsellor = RoleIn(Role.COUNSELLOR)
