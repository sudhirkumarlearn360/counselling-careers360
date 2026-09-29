"""`auth` area — staff sign-in, anyone may call.

Routes are explicit, one per line:
    path("api/<int:version>/auth/<resource>[/<id>][/<action>]", View.as_view(), name="cq.auth.<...>")
No trailing slash. Views subclass apps.common.views.ApiView (only version 1 is served).
The contract (paths, names, roles) is backend/API_ROUTES.md; tests/test_routes.py tracks what is live.
Endpoints land in Task 2 (B1).
"""

urlpatterns = []
