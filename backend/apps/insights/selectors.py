"""Ops records and insights (CQ-59, CQ-60, CQ-61). Metric definitions: counselqueue-queue-engine, Metrics."""

from __future__ import annotations

from collections import Counter

from django.db.models import Avg, Count, Q

from apps.common.choices import Clarity, Help, Outcome, Stream
from apps.queue.models import SessionRecord, Student, StudentStatus
from apps.queue.services import metrics

NO_DATA = "—"
STREAM_NAMES = dict(Stream.choices)
OUTCOME_LABELS = dict(Outcome.choices)
MAX_ROWS = 500


def students_qs(params):
    """Filters combine: q (name/mobile/token), counsellor, centre, stream, status."""
    qs = Student.objects.select_related("centre", "counsellor")
    q = (params.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(mobile__icontains=q) | Q(token__icontains=q))
    for key, field in (("counsellor", "counsellor_id"), ("centre", "centre_id")):
        if params.get(key):
            qs = qs.filter(**{field: params[key]})
    if params.get("city"):
        qs = qs.filter(centre__city__iexact=params["city"])
    if params.get("venue"):
        qs = qs.filter(centre__venue=params["venue"])
    if params.get("stream"):
        qs = qs.filter(stream=params["stream"])
    if params.get("status"):
        qs = qs.filter(status=params["status"])
    return qs


def _minutes(seconds):
    return None if seconds is None else round(seconds / 60)


def student_row(s) -> dict:
    wait = metrics.wait_seconds(s)
    session = (s.ended_at - s.started_at).total_seconds() if s.ended_at and s.started_at else None
    return {
        "id": s.id,
        "token": s.token,
        "name": s.name,
        "mobile": s.mobile,
        "school": s.school,
        "stream": s.stream,
        "course": s.course,
        "centre": {"id": s.centre_id, "city": s.centre.city},
        "date": s.centre.date.isoformat(),
        "counsellor": s.counsellor.name,
        "wait_min": _minutes(wait),
        "session_min": _minutes(session),
        "outcome": s.outcome,
        "status": s.status,
    }


def student_list(params):
    qs = students_qs(params).order_by("-checkin_at", "-id")
    matched = qs.count()
    limit = min(int(params.get("limit") or MAX_ROWS), MAX_ROWS)
    offset = int(params.get("offset") or 0)
    rows = [student_row(s) for s in qs[offset : offset + limit]]
    return rows, matched, Student.objects.count()


# --- Insights -------------------------------------------------------------------------------------


def _avg_block(values, unit="min"):
    values = [v for v in values if v is not None]
    if not values:
        return {"value": None, "n": 0, "label": NO_DATA}
    value = round(sum(values) / len(values) / 60)
    return {"value": value, "n": len(values), "label": f"{value} {unit} (from {len(values)})"}


def insights(centre=None) -> dict:
    students = Student.objects.all()
    records = SessionRecord.objects.all()
    if centre is not None:
        students, records = students.filter(centre=centre), records.filter(centre=centre)
    settings = centre.settings if centre is not None else None
    wait_promise = settings.wait_sla_min if settings else 30
    target = settings.target_session_min if settings else 15

    waits = [
        (called - queued).total_seconds()
        for called, queued in students.filter(called_at__isnull=False).values_list("called_at", "queue_at")
    ]
    sessions = [(e - s).total_seconds() for s, e in records.values_list("started_at", "ended_at")]
    rate = metrics.no_show_rate(students)

    demand = [
        {"stream": r["stream"], "name": STREAM_NAMES.get(r["stream"], r["stream"]), "count": r["n"]}
        for r in students.values("stream").annotate(n=Count("id")).order_by("-n", "stream")
    ]
    top = demand[0]["count"] if demand else 0
    for d in demand:
        d["share"] = round(d["count"] / top, 3) if top else 0  # drawn proportionally to the largest

    help_counts, clarity_counts = Counter(), Counter()
    for helps, clarity in students.values_list("help", "clarity"):
        help_counts.update(helps or [])
        if clarity:
            clarity_counts[clarity] += 1
    ranked = lambda counter, options: sorted(  # noqa: E731
        ({"option": o, "count": counter.get(o, 0)} for o in options), key=lambda r: (-r["count"], r["option"])
    )

    done = students.filter(status=StudentStatus.DONE)
    outcome_rows = [
        {"outcome": v, "label": OUTCOME_LABELS[v], "count": done.filter(outcome=v).count()}
        for v in Outcome.values
    ]
    outcome_rows.append(
        {"outcome": None, "label": "Not set", "count": done.filter(outcome__isnull=True).count()}
    )
    ratings = students.filter(rating__isnull=False).aggregate(avg=Avg("rating"), n=Count("id"))
    return {
        "headline": {
            "counselled_or_queued": metrics.counselled_or_queued(students),
            "avg_wait": {**_avg_block(waits), "promise_min": wait_promise},
            "avg_session": {**_avg_block(sessions), "target_min": target},
            "no_show_rate": {
                "value": None if rate.value is None else round(rate.value, 3),
                "label": NO_DATA
                if rate.value is None
                else f"{round(rate.value * 100)}% ({rate.numerator} of {rate.denominator})",
                "n": rate.denominator,
            },
        },
        "demand": demand,
        "help": ranked(help_counts, Help.values),
        "clarity": ranked(clarity_counts, Clarity.values),
        "outcomes": outcome_rows,
        "follow_ups": students.filter(follow_up_on__isnull=False).count(),
        "rating": {
            "avg": None if not ratings["n"] else round(float(ratings["avg"]), 1),
            "n": ratings["n"],
            "label": NO_DATA
            if not ratings["n"]
            else f"{round(float(ratings['avg']), 1)} (from {ratings['n']})",
        },
    }
