"""Shared fixtures: one live centre with one counsellor per role, used by the role matrix and later tasks."""

import datetime as dt

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Role, StaffUser
from apps.centres.models import Centre, CentreStatus
from apps.counsellors.models import Counsellor, Duty, Posting

PASSWORD = "desk123"


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def centre(db):
    return Centre.objects.create(
        city="Gwalior",
        venue="Hotel Landmark",
        date=timezone.localdate(),
        opens_at=dt.time(10, 0),
        closes_at=dt.time(18, 0),
        status=CentreStatus.LIVE,
    )


@pytest.fixture
def counsellor(db, centre):
    c = Counsellor.objects.create(name="Meera Iyer", mobile="9811022001", streams=["PCM", "PCMB"])
    Posting.objects.create(counsellor=c, centre=centre, desk_label="Desk 1", duty=Duty.ON_DESK)
    return c


@pytest.fixture
def other_counsellor(db, centre):
    c = Counsellor.objects.create(name="Rahul Sen", mobile="9811022002", streams=["COM"])
    Posting.objects.create(counsellor=c, centre=centre, desk_label="Desk 2", duty=Duty.OFF_DUTY)
    return c


@pytest.fixture
def users(db, centre, counsellor, other_counsellor):
    return {
        Role.OPS_LEAD: StaffUser.objects.create_user(
            "admin@careers360.com", "admin123", name="Admin", role=Role.OPS_LEAD
        ),
        Role.RECEPTION: StaffUser.objects.create_user(
            "desk@careers360.com", PASSWORD, name="Front Desk", role=Role.RECEPTION, centre=centre
        ),
        Role.COUNSELLOR: StaffUser.objects.create_user(
            "meera@careers360.com", PASSWORD, name="Meera Iyer", role=Role.COUNSELLOR, counsellor=counsellor
        ),
    }


def client_for(user):
    client = APIClient()
    if user is not None:
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


@pytest.fixture
def client_as(users):
    """client_as("ops_lead" | "reception" | "counsellor" | "anonymous")"""

    def make(role):
        return client_for(None if role == "anonymous" else users[role])

    return make
