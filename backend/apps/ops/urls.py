"""`ops` area — ops_lead only; spans centres, counsellors, students and insights.

Routes are explicit, one per line:
    path("api/<int:version>/ops/<resource>[/<id>][/<action>]", View.as_view(), name="cq.ops.<...>")
No trailing slash. Views subclass apps.common.views.ApiView (only version 1 is served).
The contract (paths, names, roles) is backend/API_ROUTES.md; tests/test_routes.py tracks what is live.
Views live in the owning apps (centres, counsellors, queue, insights); this module only routes them.
"""

from django.urls import path

from apps.centres import views as centre_views
from apps.counsellors import views as counsellor_views
from apps.ops import views

urlpatterns = [
    path("api/<int:version>/ops/live", views.LiveView.as_view(), name="cq.ops.live"),
    path("api/<int:version>/ops/centres", centre_views.CentresView.as_view(), name="cq.ops.centres"),
    path(
        "api/<int:version>/ops/centres/<int:centre_id>",
        centre_views.CentreDetailView.as_view(),
        name="cq.ops.centre-detail",
    ),
    path(
        "api/<int:version>/ops/centres/<int:centre_id>/go-live",
        centre_views.CentreGoLiveView.as_view(),
        name="cq.ops.centre-go-live",
    ),
    path(
        "api/<int:version>/ops/centres/<int:centre_id>/close",
        centre_views.CentreCloseView.as_view(),
        name="cq.ops.centre-close",
    ),
    path(
        "api/<int:version>/ops/counsellors",
        counsellor_views.CounsellorsView.as_view(),
        name="cq.ops.counsellors",
    ),
    path(
        "api/<int:version>/ops/counsellors/<int:counsellor_id>",
        counsellor_views.CounsellorDetailView.as_view(),
        name="cq.ops.counsellor-detail",
    ),
    path(
        "api/<int:version>/ops/counsellors/<int:counsellor_id>/postings",
        counsellor_views.CounsellorPostingsView.as_view(),
        name="cq.ops.counsellor-postings",
    ),
    path(
        "api/<int:version>/ops/postings/<int:posting_id>",
        counsellor_views.PostingDetailView.as_view(),
        name="cq.ops.posting-detail",
    ),
]
