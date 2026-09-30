"""Base pieces for every API view (routes are `api/<int:version>/<area>/...`)."""

from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

SUPPORTED_API_VERSIONS = (1,)


class ApiVersionMixin:
    """Serve only supported API versions; any other `version` path kwarg is a 404.

    Runs before authentication and permissions, so an unsupported version never leaks a 401/403.
    The version is available to handlers as `self.api_version`.
    """

    supported_versions = SUPPORTED_API_VERSIONS

    def initial(self, request, *args, **kwargs):
        version = kwargs.get("version")
        if version not in self.supported_versions:
            raise NotFound()
        self.api_version = version
        super().initial(request, *args, **kwargs)


class ApiView(ApiVersionMixin, APIView):
    """Default base class for CounselQueue endpoints."""
