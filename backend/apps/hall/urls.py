"""`hall` area — reception + ops_lead front-desk routes.

    path("api/<int:version>/hall/<resource>[/<id>][/<action>]", View.as_view(), name="cq.hall.<...>")
No trailing slash. Contract: backend/API_ROUTES.md.
"""

from django.urls import path

from apps.queue import views_hall as v

H = "api/<int:version>/hall"

urlpatterns = [
    path(f"{H}/centres/<int:centre_id>/queue", v.HallQueueView.as_view(), name="cq.hall.queue"),
    path(f"{H}/centres/<int:centre_id>/check-in", v.HallCheckInView.as_view(), name="cq.hall.check-in"),
    path(f"{H}/students/<int:student_id>", v.HallStudentView.as_view(), name="cq.hall.student-detail"),
    path(f"{H}/students/<int:student_id>/move", v.HallStudentMoveView.as_view(), name="cq.hall.student-move"),
    path(
        f"{H}/students/<int:student_id>/requeue",
        v.HallStudentRequeueView.as_view(),
        name="cq.hall.student-requeue",
    ),
    path(
        f"{H}/students/<int:student_id>/messages/<int:message_id>/resend",
        v.HallMessageResendView.as_view(),
        name="cq.hall.message-resend",
    ),
]
