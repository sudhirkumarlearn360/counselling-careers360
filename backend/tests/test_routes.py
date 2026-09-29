"""Route contract (backend/API_ROUTES.md). Each later task adds names to IMPLEMENTED as it ships them.

A name not in IMPLEMENTED is a strict xfail: once its endpoint exists and resolves, the XPASS fails the
suite until the name is flipped on here, so the contract and the code cannot drift apart.
"""

import re
from pathlib import Path

import pytest
from django.urls import resolve, reverse

from apps.common.views import ApiVersionMixin

PENDING_REASON = "endpoints land in Tasks 2–7"

# (url name, path under /api/1/, sample kwargs). Same order as API_ROUTES.md.
ROUTES = [
    ("cq.auth.login", "auth/login", {}),
    ("cq.auth.logout", "auth/logout", {}),
    ("cq.auth.refresh", "auth/refresh", {}),
    ("cq.auth.me", "auth/me", {}),
    ("cq.public.centre-detail", "public/centres/<centre_slug>", {"centre_slug": "gwalior-demo"}),
    ("cq.public.otp-send", "public/centres/<centre_slug>/otp/send", {"centre_slug": "gwalior-demo"}),
    ("cq.public.otp-verify", "public/centres/<centre_slug>/otp/verify", {"centre_slug": "gwalior-demo"}),
    ("cq.public.check-in", "public/centres/<centre_slug>/check-in", {"centre_slug": "gwalior-demo"}),
    ("cq.public.token-detail", "public/tokens/<access_key>", {"access_key": "abc.def"}),
    ("cq.public.token-release", "public/tokens/<access_key>/release", {"access_key": "abc.def"}),
    ("cq.public.token-consent", "public/tokens/<access_key>/consent", {"access_key": "abc.def"}),
    ("cq.public.token-rating", "public/tokens/<access_key>/rating", {"access_key": "abc.def"}),
    ("cq.public.board", "public/board/<centre_slug>", {"centre_slug": "gwalior-demo"}),
    ("cq.ops.live", "ops/live", {}),
    ("cq.ops.centres", "ops/centres", {}),
    ("cq.ops.centre-detail", "ops/centres/<centre_id>", {"centre_id": 1}),
    ("cq.ops.centre-go-live", "ops/centres/<centre_id>/go-live", {"centre_id": 1}),
    ("cq.ops.centre-close", "ops/centres/<centre_id>/close", {"centre_id": 1}),
    ("cq.ops.counsellors", "ops/counsellors", {}),
    ("cq.ops.counsellor-detail", "ops/counsellors/<counsellor_id>", {"counsellor_id": 3}),
    ("cq.ops.counsellor-postings", "ops/counsellors/<counsellor_id>/postings", {"counsellor_id": 3}),
    ("cq.ops.posting-detail", "ops/postings/<posting_id>", {"posting_id": 4}),
    ("cq.ops.students", "ops/students", {}),
    ("cq.ops.students-export", "ops/students/export", {}),
    ("cq.ops.insights", "ops/insights", {}),
    ("cq.hall.queue", "hall/centres/<centre_id>/queue", {"centre_id": 1}),
    ("cq.hall.check-in", "hall/centres/<centre_id>/check-in", {"centre_id": 1}),
    ("cq.hall.student-detail", "hall/students/<student_id>", {"student_id": 2}),
    ("cq.hall.student-move", "hall/students/<student_id>/move", {"student_id": 2}),
    ("cq.hall.student-requeue", "hall/students/<student_id>/requeue", {"student_id": 2}),
    (
        "cq.hall.message-resend",
        "hall/students/<student_id>/messages/<message_id>/resend",
        {"student_id": 2, "message_id": 5},
    ),
    ("cq.desk.queue", "desk/queue", {}),
    ("cq.desk.duty", "desk/duty", {}),
    ("cq.desk.call-next", "desk/call-next", {}),
    ("cq.desk.call-token", "desk/call-token", {}),
    ("cq.desk.student-detail", "desk/students/<student_id>", {"student_id": 2}),
    ("cq.desk.student-start", "desk/students/<student_id>/start", {"student_id": 2}),
    ("cq.desk.student-complete", "desk/students/<student_id>/complete", {"student_id": 2}),
    ("cq.desk.student-missed", "desk/students/<student_id>/missed", {"student_id": 2}),
    ("cq.desk.student-pull-forward", "desk/students/<student_id>/pull-forward", {"student_id": 2}),
    ("cq.desk.student-consent", "desk/students/<student_id>/consent", {"student_id": 2}),
    ("cq.desk.student-consent-request", "desk/students/<student_id>/consent-request", {"student_id": 2}),
    ("cq.desk.student-notes", "desk/students/<student_id>/notes", {"student_id": 2}),
    (
        "cq.desk.message-resend",
        "desk/students/<student_id>/messages/<message_id>/resend",
        {"student_id": 2, "message_id": 5},
    ),
    ("cq.desk.my-students", "desk/my-students", {}),
    ("cq.desk.my-centres", "desk/my-centres", {}),
    ("cq.webhooks.messaging-status", "webhooks/messaging/status", {}),
]

# Flip names on as their endpoints land (Tasks 2–7).
IMPLEMENTED: set = set()


def _expected_path(path, kwargs):
    return "/api/1/" + re.sub(r"<(\w+)>", lambda m: str(kwargs[m.group(1)]), path)


def _params():
    for name, path, kwargs in ROUTES:
        marks = () if name in IMPLEMENTED else (pytest.mark.xfail(reason=PENDING_REASON, strict=True),)
        yield pytest.param(name, path, kwargs, id=name, marks=marks)


@pytest.mark.parametrize("name, path, kwargs", list(_params()))
def test_route_resolves_to_versioned_view(name, path, kwargs):
    url = reverse(name, kwargs={"version": 1, **kwargs})
    assert url == _expected_path(path, kwargs)
    match = resolve(url)
    assert issubclass(match.func.view_class, ApiVersionMixin)


def test_route_list_matches_api_routes_md():
    md = (Path(__file__).resolve().parent.parent / "API_ROUTES.md").read_text()
    table = re.findall(r"^\| [A-Z, ]+ \| `([^`]+)` \| (cq\.[\w.-]+) \|", md, flags=re.M)
    assert [(n, p) for p, n in table] == [(n, p) for n, p, _ in ROUTES]


def test_implemented_names_are_in_the_contract():
    assert IMPLEMENTED <= {name for name, _, _ in ROUTES}


def test_every_area_has_its_own_url_module():
    from config.urls import API_AREA_MODULES

    assert API_AREA_MODULES == [
        "apps.accounts.urls",
        "apps.public.urls",
        "apps.ops.urls",
        "apps.hall.urls",
        "apps.desk.urls",
        "apps.messaging.urls",
    ]
