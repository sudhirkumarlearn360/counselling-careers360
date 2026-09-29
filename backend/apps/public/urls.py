"""`public` area — student-facing and hall-screen routes, no login.

Routes are explicit, one per line:
    path("api/<int:version>/public/<resource>[/<id>][/<action>]", View.as_view(), name="cq.public.<...>")
No trailing slash. Views subclass apps.common.views.ApiView (only version 1 is served).
The contract (paths, names, roles) is backend/API_ROUTES.md; tests/test_routes.py tracks what is live.
Endpoints land in Tasks 4 and 6-7.
"""

urlpatterns = []
