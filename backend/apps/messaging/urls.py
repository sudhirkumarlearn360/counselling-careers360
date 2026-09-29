"""`webhooks` area — provider callbacks (signed)."""

from django.urls import path

from apps.messaging import views

urlpatterns = [
    path(
        "api/<int:version>/webhooks/messaging/status",
        views.MessagingStatusView.as_view(),
        name="cq.webhooks.messaging-status",
    ),
]
