import pytest
from rest_framework import serializers
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.common.exceptions import DomainError


class Boom(APIView):
    permission_classes = []
    exc = None

    def get(self, request):
        raise self.exc


def call(exc):
    view = Boom.as_view(exc=exc)
    return view(APIRequestFactory().get("/x"))


def test_domain_error_maps_to_400_code_message_data():
    resp = call(
        DomainError(
            "Finish PCM-02 before calling the next student.", code="desk_busy", data={"token": "PCM-02"}
        )
    )
    assert resp.status_code == 400
    assert resp.data == {
        "code": "desk_busy",
        "message": "Finish PCM-02 before calling the next student.",
        "data": {"token": "PCM-02"},
    }


def test_validation_error_uses_same_shape_with_all_fields():
    resp = call(serializers.ValidationError({"name": ["Enter your school."], "mobile": ["bad"]}))
    assert resp.status_code == 400
    assert resp.data["code"] == "invalid"
    assert resp.data["data"]["fields"] == {"name": ["Enter your school."], "mobile": ["bad"]}


@pytest.mark.parametrize("status", [401, 403, 404])
def test_other_api_errors_keep_status_and_shape(status):
    from rest_framework import exceptions

    exc = {401: exceptions.NotAuthenticated(), 403: exceptions.PermissionDenied(), 404: exceptions.NotFound()}
    resp = call(exc[status])
    assert resp.status_code == status
    assert set(resp.data) == {"code", "message", "data"}
