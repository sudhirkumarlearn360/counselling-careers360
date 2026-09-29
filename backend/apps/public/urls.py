"""`public` area — student-facing and hall-screen routes, no login.

Routes are explicit, one per line:
    path("api/<int:version>/public/<resource>[/<id>][/<action>]", View.as_view(), name="cq.public.<...>")
No trailing slash. Views subclass apps.common.views.ApiView (only version 1 is served).
The contract (paths, names, roles) is backend/API_ROUTES.md; tests/test_routes.py tracks what is live.
"""

from django.urls import path

from apps.public import views

P = "api/<int:version>/public"

urlpatterns = [
    path(f"{P}/centres/<slug:centre_slug>", views.CentreDetailView.as_view(), name="cq.public.centre-detail"),
    path(f"{P}/centres/<slug:centre_slug>/otp/send", views.OtpSendView.as_view(), name="cq.public.otp-send"),
    path(
        f"{P}/centres/<slug:centre_slug>/otp/verify",
        views.OtpVerifyView.as_view(),
        name="cq.public.otp-verify",
    ),
    path(f"{P}/centres/<slug:centre_slug>/check-in", views.CheckInView.as_view(), name="cq.public.check-in"),
    path(f"{P}/tokens/<str:access_key>", views.TokenDetailView.as_view(), name="cq.public.token-detail"),
    path(
        f"{P}/tokens/<str:access_key>/release",
        views.TokenReleaseView.as_view(),
        name="cq.public.token-release",
    ),
    path(
        f"{P}/tokens/<str:access_key>/consent",
        views.TokenConsentView.as_view(),
        name="cq.public.token-consent",
    ),
    path(
        f"{P}/tokens/<str:access_key>/rating", views.TokenRatingView.as_view(), name="cq.public.token-rating"
    ),
    path(f"{P}/board/<slug:centre_slug>", views.BoardView.as_view(), name="cq.public.board"),
]
