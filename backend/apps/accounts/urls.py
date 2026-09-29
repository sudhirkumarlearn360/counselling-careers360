"""`auth` area — staff sign-in, anyone may call.

Routes are explicit, one per line:
    path("api/<int:version>/auth/<resource>[/<id>][/<action>]", View.as_view(), name="cq.auth.<...>")
No trailing slash. Views subclass apps.common.views.ApiView (only version 1 is served).
The contract (paths, names, roles) is backend/API_ROUTES.md; tests/test_routes.py tracks what is live.
"""

from django.urls import path

from apps.accounts import views

urlpatterns = [
    path("api/<int:version>/auth/login", views.LoginView.as_view(), name="cq.auth.login"),
    path("api/<int:version>/auth/logout", views.LogoutView.as_view(), name="cq.auth.logout"),
    path("api/<int:version>/auth/refresh", views.RefreshView.as_view(), name="cq.auth.refresh"),
    path("api/<int:version>/auth/me", views.MeView.as_view(), name="cq.auth.me"),
]
