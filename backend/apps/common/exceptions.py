"""Domain errors and the single DRF exception handler.

Every error response has the shape ``{"code": str, "message": str, "data": dict}``.
Services raise ``DomainError`` subclasses (e.g. ``apps.queue.exceptions``) with the exact
counselqueue-ui-spec string as ``message``; they map to HTTP 400.
"""

from __future__ import annotations

from typing import Any

from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class DomainError(Exception):
    code = "domain_error"
    message = ""
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(
        self, message: str | None = None, code: str | None = None, data: dict[str, Any] | None = None
    ):
        self.message = message if message is not None else self.message
        if code is not None:
            self.code = code
        self.data = data or {}
        super().__init__(self.message)


def _first_message(detail: Any) -> str:
    if isinstance(detail, dict):
        for value in detail.values():
            return _first_message(value)
        return ""
    if isinstance(detail, (list, tuple)):
        return _first_message(detail[0]) if detail else ""
    return str(detail)


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return Response({"code": exc.code, "message": exc.message, "data": exc.data}, status=exc.status_code)

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, drf_exceptions.ValidationError):
        detail = exc.detail
        fields = detail if isinstance(detail, dict) else {"non_field_errors": detail}
        response.data = {"code": "invalid", "message": _first_message(detail), "data": {"fields": fields}}
    elif isinstance(exc, drf_exceptions.Throttled):
        response.data = {
            "code": "throttled",
            "message": "Too many attempts — try again in a minute.",
            "data": {"retry_after": int(exc.wait or 60)},
        }
    elif isinstance(exc, drf_exceptions.APIException):
        codes = exc.get_codes()
        code = codes if isinstance(codes, str) else exc.default_code
        response.data = {"code": code, "message": _first_message(exc.detail), "data": {}}
    return response
