"""Role x endpoint matrix. Later tasks extend MATRIX by adding rows (one per endpoint).

Each row: (method, url, {role: expected status}). Roles: anonymous, ops_lead, reception, counsellor.
Bodies are omitted on purpose: authentication and role checks run before validation, so a 403/401 is
decided first; rows expecting 200 must be GETs (or POSTs that need no body).
"""

import pytest

ROLES = ["anonymous", "ops_lead", "reception", "counsellor"]


def row(method, url, anonymous, ops_lead, reception, counsellor):
    return (
        method,
        url,
        {"anonymous": anonymous, "ops_lead": ops_lead, "reception": reception, "counsellor": counsellor},
    )


MATRIX = [
    row("GET", "/api/1/auth/me", 401, 200, 200, 200),
    row("POST", "/api/1/auth/logout", 400, 400, 400, 400),  # open to anyone; 400 = no refresh token sent
    row("GET", "/api/1/ops/live", 401, 200, 403, 403),
    # Task 3. `{centre_id}`, `{counsellor_id}`, `{posting_id}` are filled from the fixtures.
    # An empty body: writes that need a body answer 400 to ops (auth and role are decided first).
    row("GET", "/api/1/ops/centres", 401, 200, 403, 403),
    row("POST", "/api/1/ops/centres", 401, 400, 403, 403),
    row("GET", "/api/1/ops/centres/{centre_id}", 401, 200, 403, 403),
    row("PATCH", "/api/1/ops/centres/{centre_id}", 401, 200, 403, 403),
    row("POST", "/api/1/ops/centres/{centre_id}/go-live", 401, 400, 403, 403),  # live already
    row("GET", "/api/1/ops/centres/{centre_id}/close", 401, 200, 403, 403),
    row("POST", "/api/1/ops/centres/{centre_id}/close", 401, 409, 403, 403),  # needs confirm
    row("GET", "/api/1/ops/counsellors", 401, 200, 403, 403),
    row("POST", "/api/1/ops/counsellors", 401, 400, 403, 403),
    row("GET", "/api/1/ops/counsellors/{counsellor_id}", 401, 200, 403, 403),
    row("PATCH", "/api/1/ops/counsellors/{counsellor_id}", 401, 200, 403, 403),
    row("GET", "/api/1/ops/counsellors/{counsellor_id}/postings", 401, 200, 403, 403),
    row("POST", "/api/1/ops/counsellors/{counsellor_id}/postings", 401, 400, 403, 403),
    row("PATCH", "/api/1/ops/postings/{posting_id}", 401, 200, 403, 403),
    # desk/duty: ops needs ?as_counsellor (400); the counsellor sends no duty (400); reception 403.
    row("POST", "/api/1/desk/duty", 401, 400, 403, 400),
    # Task 5+: hall (reception + ops), desk (counsellor; ops needs ?as_counsellor), ops records.
    row("GET", "/api/1/hall/centres/{centre_id}/queue", 401, 200, 200, 403),
    row("POST", "/api/1/hall/centres/{centre_id}/check-in", 401, 400, 400, 403),
    row("GET", "/api/1/desk/queue", 401, 400, 403, 200),
    row("POST", "/api/1/desk/call-next", 401, 400, 403, 400),  # counsellor: empty queue
    row("GET", "/api/1/desk/my-students", 401, 400, 403, 200),
    row("GET", "/api/1/desk/my-centres", 401, 400, 403, 200),
    row("GET", "/api/1/ops/students", 401, 200, 403, 403),
    row("GET", "/api/1/ops/students/export", 401, 200, 403, 403),
    row("GET", "/api/1/ops/insights", 401, 200, 403, 403),
]


def _cases():
    for method, url, expected in MATRIX:
        for role in ROLES:
            yield pytest.param(method, url, role, expected[role], id=f"{method} {url} as {role}")


@pytest.mark.django_db
@pytest.mark.parametrize("method, url, role, expected", list(_cases()))
def test_role_matrix(client_as, centre, counsellor, method, url, role, expected):
    url = url.format(
        centre_id=centre.id, counsellor_id=counsellor.id, posting_id=counsellor.postings.get().id
    )
    resp = client_as(role).generic(method, url)
    assert resp.status_code == expected, resp.content
    if expected in (401, 403):
        assert set(resp.json()) == {"code", "message", "data"}


@pytest.mark.django_db
def test_matrix_rows_cover_all_four_roles():
    for _, _, expected in MATRIX:
        assert set(expected) == set(ROLES)
