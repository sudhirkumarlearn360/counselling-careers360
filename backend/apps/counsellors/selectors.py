from __future__ import annotations

from django.db.models import Prefetch

from apps.counsellors.models import Counsellor, Posting


def counsellors_qs():
    return Counsellor.objects.prefetch_related(
        Prefetch("postings", queryset=Posting.objects.select_related("centre").order_by("centre__date", "id"))
    )


def posting_payload(p: Posting) -> dict:
    return {
        "id": p.id,
        "counsellor_id": p.counsellor_id,
        "centre_id": p.centre_id,
        "city": p.centre.city,
        "venue": p.centre.venue,
        "date": p.centre.date.isoformat(),
        "centre_status": p.centre.status,
        "desk_label": p.desk_label,
        "duty": p.duty,
    }


def counsellor_stats() -> dict:
    """Done sessions, average session and 'ready to apply' per counsellor, from SessionRecord (2 queries)."""
    from collections import defaultdict

    from apps.queue.models import SessionRecord

    done, secs, ready = defaultdict(int), defaultdict(float), defaultdict(int)
    for r in SessionRecord.objects.values("counsellor_id", "started_at", "ended_at", "outcome"):
        done[r["counsellor_id"]] += 1
        secs[r["counsellor_id"]] += (r["ended_at"] - r["started_at"]).total_seconds()
        ready[r["counsellor_id"]] += r["outcome"] == "ready"
    return {
        cid: {
            "done": n,
            "avg_session_min": round(secs[cid] / n / 60) if n else None,
            "ready_to_apply": ready[cid],
        }
        for cid, n in done.items()
    }


def counsellor_payload(c: Counsellor, stats: dict = None) -> dict:
    stats = (stats or {}).get(c.id, {"done": 0, "avg_session_min": None, "ready_to_apply": 0})
    return {
        "stats": stats,
        "id": c.id,
        "name": c.name,
        "mobile": c.mobile,
        "streams": c.streams,
        "expected_session_min": c.expected_session_min,
        "postings": [posting_payload(p) for p in c.postings.all()],  # prefetched
    }


def counsellor_list() -> list:
    stats = counsellor_stats()
    return [counsellor_payload(c, stats) for c in counsellors_qs()]


def counsellor_by_id(pk: int):
    return counsellors_qs().filter(pk=pk).first()


def posting_by_id(pk: int):
    return Posting.objects.select_related("centre", "counsellor").filter(pk=pk).first()
