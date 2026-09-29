"""The reusable as_counsellor desk-context mixin (CQ-5), exercised through a throwaway view."""

import pytest
from django.urls import path
from rest_framework.response import Response

from apps.accounts.desk_context import AsCounsellorMixin
from apps.accounts.permissions import RoleIn
from apps.common.views import ApiView
from tests.conftest import client_for


class Probe(AsCounsellorMixin, ApiView):
    permission_classes = [RoleIn("counsellor", "ops_lead")]

    def get(self, request, **kwargs):
        return Response(
            {
                "data": {
                    "counsellor": self.desk_counsellor.id,
                    "on_behalf_of": self.on_behalf_of.id if self.on_behalf_of else None,
                    "acting_as_lead": self.acting_as_lead,
                }
            }
        )


class ReceptionOnly(ApiView):
    permission_classes = [RoleIn("reception")]

    def get(self, request, **kwargs):
        return Response({"data": "ok"})


urlpatterns = [
    path("api/<int:version>/test/desk", Probe.as_view(), name="cq.test.desk"),
    path("api/<int:version>/test/hall", ReceptionOnly.as_view(), name="cq.test.hall"),
]
pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.accounts.test_cq5_as_counsellor")]


def test_cq5_counsellor_gets_own_desk_and_no_on_behalf_of(client_as, counsellor):
    resp = client_as("counsellor").get("/api/1/test/desk")
    assert resp.json()["data"] == {"counsellor": counsellor.id, "on_behalf_of": None, "acting_as_lead": False}


def test_cq5_ops_lead_with_param_sets_on_behalf_of(client_as, other_counsellor):
    resp = client_as("ops_lead").get(f"/api/1/test/desk?as_counsellor={other_counsellor.id}")
    assert resp.status_code == 200
    assert resp.json()["data"] == {
        "counsellor": other_counsellor.id,
        "on_behalf_of": other_counsellor.id,
        "acting_as_lead": True,
    }


def test_cq5_counsellor_cannot_use_as_counsellor_even_for_self(client_as, counsellor, other_counsellor):
    for target in (other_counsellor.id, counsellor.id):
        resp = client_as("counsellor").get(f"/api/1/test/desk?as_counsellor={target}")
        assert resp.status_code == 403
        assert resp.json()["code"] == "as_counsellor_forbidden"


def test_cq5_ops_lead_without_param_gets_clear_400(client_as):
    resp = client_as("ops_lead").get("/api/1/test/desk")
    assert resp.status_code == 400 and resp.json()["code"] == "as_counsellor_required"


@pytest.mark.parametrize("bad", ["abc", "0", "99999"])
def test_cq5_unknown_or_malformed_counsellor_is_404(client_as, bad):
    resp = client_as("ops_lead").get(f"/api/1/test/desk?as_counsellor={bad}")
    assert resp.status_code == 404


def test_cq5_reception_is_403_role_not_allowed(client_as, counsellor):
    resp = client_as("reception").get(f"/api/1/test/desk?as_counsellor={counsellor.id}")
    assert resp.status_code == 403 and resp.json()["code"] == "role_not_allowed"


def test_cq5_anonymous_is_401(client_as):
    assert client_as("anonymous").get("/api/1/test/desk").status_code == 401


def test_cq5_role_in_allows_only_listed_roles(client_as):
    assert client_as("reception").get("/api/1/test/hall").status_code == 200
    for role in ("ops_lead", "counsellor"):
        resp = client_as(role).get("/api/1/test/hall")
        assert resp.status_code == 403 and resp.json()["code"] == "role_not_allowed"


def test_cq5_role_in_rejects_unknown_role_names():
    with pytest.raises(ValueError):
        RoleIn("janitor")


def test_cq5_ops_lead_may_pass_the_counsellor_of_a_client_helper(users, counsellor):
    resp = client_for(users["ops_lead"]).get(f"/api/1/test/desk?as_counsellor={counsellor.id}")
    assert resp.json()["data"]["on_behalf_of"] == counsellor.id


def test_cq5_counsellor_role_without_linked_counsellor_is_403_role_not_allowed():
    from types import SimpleNamespace

    from rest_framework.exceptions import PermissionDenied

    mixin = AsCounsellorMixin()
    request = SimpleNamespace(user=SimpleNamespace(role="counsellor", counsellor=None), query_params={})
    with pytest.raises(PermissionDenied) as exc:
        mixin._resolve_desk_context(request)
    assert exc.value.get_codes() == "role_not_allowed"
