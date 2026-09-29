"""`hall` area — reception + ops_lead front-desk routes.

Routes are explicit, one per line:
    path("api/<int:version>/hall/<resource>[/<id>][/<action>]", View.as_view(), name="cq.hall.<...>")
No trailing slash. Views subclass apps.common.views.ApiView (only version 1 is served).
The contract (paths, names, roles) is backend/API_ROUTES.md; tests/test_routes.py tracks what is live.
Views live in apps.queue; this module only routes them.
"""

urlpatterns = []
