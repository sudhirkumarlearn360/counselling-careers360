"""Every CMS user can see the student check-in link of the centres they can reach."""

import pytest
from django.test import override_settings

pytestmark = pytest.mark.django_db


def expected(centre, base="http://localhost:5173"):
    return f"{base}/c/{centre.slug}"


def test_reception_gets_the_link_for_their_centre(client_as, centre):
    me = client_as("reception").get("/api/1/auth/me").json()["data"]
    assert me["centre"]["student_url"] == expected(centre)


def test_counsellor_gets_the_link_for_each_posted_centre(client_as, centre, counsellor):
    rows = client_as("counsellor").get("/api/1/desk/my-centres").json()["data"]
    assert rows[0]["centre"]["student_url"] == expected(centre)


def test_ops_lead_gets_the_link_on_centres_and_live_centres(client_as, centre, counsellor):
    c = client_as("ops_lead")
    assert c.get("/api/1/ops/centres").json()["data"][0]["student_url"] == expected(centre)
    assert c.get("/api/1/ops/live").json()["data"][0]["student_url"] == expected(centre)


@override_settings(FRONTEND_BASE_URL="https://counsel.careers360.com/")
def test_the_link_uses_the_configured_base_and_never_doubles_the_slash(client_as, centre):
    me = client_as("reception").get("/api/1/auth/me").json()["data"]
    assert me["centre"]["student_url"] == f"https://counsel.careers360.com/c/{centre.slug}"


def test_the_link_points_at_a_page_that_exists(client_as, centre):
    slug = (
        client_as("reception").get("/api/1/auth/me").json()["data"]["centre"]["student_url"].rsplit("/", 1)[1]
    )
    assert client_as("anonymous").get(f"/api/1/public/centres/{slug}").status_code == 200
