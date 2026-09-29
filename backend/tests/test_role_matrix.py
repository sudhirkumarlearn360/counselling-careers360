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
]


def _cases():
    for method, url, expected in MATRIX:
        for role in ROLES:
            yield pytest.param(method, url, role, expected[role], id=f"{method} {url} as {role}")


@pytest.mark.django_db
@pytest.mark.parametrize("method, url, role, expected", list(_cases()))
def test_role_matrix(client_as, method, url, role, expected):
    resp = client_as(role).generic(method, url)
    assert resp.status_code == expected, resp.content
    if expected in (401, 403):
        assert set(resp.json()) == {"code", "message", "data"}


@pytest.mark.django_db
def test_matrix_rows_cover_all_four_roles():
    for _, _, expected in MATRIX:
        assert set(expected) == set(ROLES)
