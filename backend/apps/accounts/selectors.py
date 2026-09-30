"""Read side of sign-in: what a user sees (nav, default screen, centre/desk context). CQ-1/3."""

from __future__ import annotations

from django.conf import settings
from django.utils import timezone

from apps.accounts.models import Role
from apps.centres.models import CentreStatus
from apps.counsellors.models import Posting

# (key, label) in display order. The first item is the role's default screen (CQ-3).
NAV = {
    Role.RECEPTION: [
        ("hall_queue", "Hall queue"),
        ("add_student", "Add a student"),
        ("hall_board", "Hall board"),
    ],
    Role.COUNSELLOR: [
        ("my_queue", "My queue"),
        ("live_session", "Live session"),
        ("my_students", "My students"),
        ("my_centres", "My centres"),
    ],
    Role.OPS_LEAD: [
        ("live_centres", "Live centres"),
        ("centres_dates", "Centres & dates"),
        ("counsellors", "Counsellors"),
        ("all_students", "All students"),
        ("insights", "Insights"),
        ("hall_queue", "Hall queue"),
        ("hall_board", "Hall board"),
    ],
}


def nav_for(role: str) -> list:
    return [{"key": key, "label": label} for key, label in NAV[role]]


def default_view_for(role: str) -> str:
    return NAV[role][0][0]


def student_url(centre) -> str:
    """The student's check-in page for this centre (what the QR code opens)."""
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/c/{centre.slug}"


def centre_payload(centre) -> dict:
    return {
        "student_url": student_url(centre),
        "id": centre.id,
        "city": centre.city,
        "venue": centre.venue,
        "date": centre.date.isoformat(),
        "slug": centre.slug,
        "status": centre.status,
        "opens_at": centre.opens_at.strftime("%H:%M"),
        "closes_at": centre.closes_at.strftime("%H:%M"),
    }


def current_posting(counsellor_id):
    """A counsellor's current posting = their posting at today's live centre (domain skill)."""
    return (
        Posting.objects.select_related("centre")
        .filter(
            counsellor_id=counsellor_id, centre__status=CentreStatus.LIVE, centre__date=timezone.localdate()
        )
        .order_by("centre__opens_at", "id")
        .first()
    )


def user_payload(user) -> dict:
    """Shared by login and `auth/me`. Centre/desk come from the account, never picked by the user."""
    centre = posting = None
    if user.role == Role.RECEPTION:
        centre = user.centre
    elif user.role == Role.COUNSELLOR:
        posting = current_posting(user.counsellor_id)
        centre = posting.centre if posting else None
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "title": user.title,
        "role": user.role,
        "counsellor": user.counsellor_id,
        "default_view": default_view_for(user.role),
        "nav": nav_for(user.role),
        "centre": centre_payload(centre) if centre else None,
        "posting": {"id": posting.id, "desk_label": posting.desk_label, "duty": posting.duty}
        if posting
        else None,
    }
