"""Root URLs. Each app's API is mounted under /api/ by later tasks (B1-B7)."""

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    # path("api/auth/", include("apps.accounts.urls")),
    # path("api/", include("apps.centres.urls")),
    # path("api/", include("apps.counsellors.urls")),
    # path("api/", include("apps.queue.urls")),
    # path("api/messaging/", include("apps.messaging.urls")),
    # path("api/insights/", include("apps.insights.urls")),
    # path("api/public/", include("apps.public.urls")),
]
