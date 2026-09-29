"""`ops` area — ops_lead only; spans centres, counsellors, students and insights.

Routes are explicit, one per line:
    path("api/<int:version>/ops/<resource>[/<id>][/<action>]", View.as_view(), name="cq.ops.<...>")
No trailing slash. Views subclass apps.common.views.ApiView (only version 1 is served).
The contract (paths, names, roles) is backend/API_ROUTES.md; tests/test_routes.py tracks what is live.
Views live in the owning apps (centres, counsellors, queue, insights); this module only routes them.
"""

from django.urls import path

from apps.ops import views

urlpatterns = [
    path("api/<int:version>/ops/live", views.LiveView.as_view(), name="cq.ops.live"),
]
