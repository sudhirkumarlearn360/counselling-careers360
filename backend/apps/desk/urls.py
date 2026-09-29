"""`desk` area — counsellor, or ops_lead with ?as_counsellor=<counsellor_id>.

    path("api/<int:version>/desk/<resource>[/<id>][/<action>]", View.as_view(), name="cq.desk.<...>")
No trailing slash. Contract: backend/API_ROUTES.md.
"""

from django.urls import path

from apps.counsellors import views as counsellor_views
from apps.queue import views_desk as v

D = "api/<int:version>/desk"
S = f"{D}/students/<int:student_id>"

urlpatterns = [
    path(f"{D}/queue", v.DeskQueueView.as_view(), name="cq.desk.queue"),
    path(f"{D}/duty", counsellor_views.DutyView.as_view(), name="cq.desk.duty"),
    path(f"{D}/call-next", v.DeskCallNextView.as_view(), name="cq.desk.call-next"),
    path(f"{D}/call-token", v.DeskCallTokenView.as_view(), name="cq.desk.call-token"),
    path(S, v.DeskStudentView.as_view(), name="cq.desk.student-detail"),
    path(f"{S}/start", v.DeskStartView.as_view(), name="cq.desk.student-start"),
    path(f"{S}/complete", v.DeskCompleteView.as_view(), name="cq.desk.student-complete"),
    path(f"{S}/missed", v.DeskMissedView.as_view(), name="cq.desk.student-missed"),
    path(f"{S}/pull-forward", v.DeskPullForwardView.as_view(), name="cq.desk.student-pull-forward"),
    path(f"{S}/consent", v.DeskConsentView.as_view(), name="cq.desk.student-consent"),
    path(f"{S}/consent-request", v.DeskConsentRequestView.as_view(), name="cq.desk.student-consent-request"),
    path(f"{S}/notes", v.DeskNotesView.as_view(), name="cq.desk.student-notes"),
    path(
        f"{S}/messages/<int:message_id>/resend",
        v.DeskMessageResendView.as_view(),
        name="cq.desk.message-resend",
    ),
    path(f"{D}/my-students", v.DeskMyStudentsView.as_view(), name="cq.desk.my-students"),
    path(f"{D}/my-centres", v.DeskMyCentresView.as_view(), name="cq.desk.my-centres"),
]
