"""`webhooks` area — provider callbacks (signed).

Routes are explicit, one per line:
    path("api/<int:version>/webhooks/<resource>[/<id>][/<action>]", View.as_view(), name="cq.webhooks.<...>")
No trailing slash. Views subclass apps.common.views.ApiView (only version 1 is served).
The contract (paths, names, roles) is backend/API_ROUTES.md; tests/test_routes.py tracks what is live.
Endpoint lands with messaging delivery status (CQ-58).
"""

urlpatterns = []
