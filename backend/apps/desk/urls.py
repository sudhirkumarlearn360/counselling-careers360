"""`desk` area — counsellor, or ops_lead with ?as_counsellor=<counsellor_id>.

Routes are explicit, one per line:
    path("api/<int:version>/desk/<resource>[/<id>][/<action>]", View.as_view(), name="cq.desk.<...>")
No trailing slash. Views subclass apps.common.views.ApiView (only version 1 is served).
The contract (paths, names, roles) is backend/API_ROUTES.md; tests/test_routes.py tracks what is live.
Views live in apps.queue / apps.counsellors; this module only routes them.
"""

urlpatterns = []
