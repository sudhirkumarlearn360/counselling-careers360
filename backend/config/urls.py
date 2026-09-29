"""Root URLs: one module per API area (area = who calls it). Each module declares full
`api/<int:version>/<area>/...` paths itself; see backend/API_ROUTES.md for the contract."""

from django.contrib import admin
from django.urls import include, path

API_AREA_MODULES = [
    "apps.accounts.urls",  # auth
    "apps.public.urls",  # public
    "apps.ops.urls",  # ops
    "apps.hall.urls",  # hall
    "apps.desk.urls",  # desk
    "apps.messaging.urls",  # webhooks
]

urlpatterns = [path("admin/", admin.site.urls)] + [path("", include(module)) for module in API_AREA_MODULES]
