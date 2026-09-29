"""Auth area (anyone / staff). Thin: validate, call a service, wrap in the envelope."""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts import selectors, services
from apps.common.exceptions import DomainError
from apps.common.views import ApiView


class LoginView(ApiView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, **kwargs):
        user, refresh = services.sign_in(request.data.get("email"), request.data.get("password"))
        return Response(
            {
                "data": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": selectors.user_payload(user),
                    **services.failure_data(0),
                }
            }
        )


class RefreshTokenInvalid(APIException):
    """401 even though this view has no authenticators (DRF would turn an auth error into 403)."""

    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "token_not_valid"
    default_detail = "Your session has ended. Sign in again."


class RefreshView(ApiView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, **kwargs):
        serializer = TokenRefreshSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise RefreshTokenInvalid() from exc
        return Response({"data": serializer.validated_data})


class RefreshRequired(DomainError):
    code = "refresh_required"
    message = "Send the refresh token to sign out."


class LogoutView(ApiView):
    permission_classes = [IsAuthenticated]

    def post(self, request, **kwargs):
        raw = request.data.get("refresh")
        if not raw or not isinstance(raw, str):
            raise RefreshRequired()
        try:
            token = RefreshToken(raw)
        except TokenError:
            # Expired or already blacklisted: nothing left to invalidate, so signing out is a success.
            return Response({"data": {"signed_out": True}})
        if str(token.get("user_id")) != str(request.user.pk):
            raise ValidationError({"refresh": ["That token belongs to another account."]})
        token.blacklist()
        return Response({"data": {"signed_out": True}})


class MeView(ApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request, **kwargs):
        return Response({"data": selectors.user_payload(request.user)})
