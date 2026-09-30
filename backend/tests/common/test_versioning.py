"""Only API version 1 is served; any other version is a 404 in the standard error shape."""

import pytest
from django.urls import path
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from apps.common.views import ApiVersionMixin


class Ping(ApiVersionMixin, APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, **kwargs):
        return Response({"data": {"version": self.api_version}})


urlpatterns = [path("api/<int:version>/test/ping", Ping.as_view(), name="cq.test.ping")]


@pytest.mark.urls("tests.common.test_versioning")
def test_version_1_is_served():
    resp = APIClient().get("/api/1/test/ping")
    assert resp.status_code == 200
    assert resp.json() == {"data": {"version": 1}}


@pytest.mark.urls("tests.common.test_versioning")
@pytest.mark.parametrize("version", [0, 2, 99])
def test_other_versions_are_404(version):
    resp = APIClient().get(f"/api/{version}/test/ping")
    assert resp.status_code == 404
    assert set(resp.json()) == {"code", "message", "data"}
    assert resp.json()["code"] == "not_found"


@pytest.mark.urls("tests.common.test_versioning")
def test_trailing_slash_is_not_redirected():
    resp = APIClient().get("/api/1/test/ping/")
    assert resp.status_code == 404
