"""Real MySQL races (TransactionTestCase semantics: each thread has its own connection and commits).

Queue-engine "Concurrency": asserting that lock calls were made is not enough, so every test here
starts the competing calls together on a barrier and checks the committed end state.
"""

from __future__ import annotations

import threading
from collections import Counter

import pytest
from django.db import connection

from apps.centres.exceptions import CentreNotLive as CloseRefused
from apps.centres.models import Centre, CentreStatus
from apps.queue.exceptions import CentreNotLive, DeskBusy, DuplicateToken
from apps.queue.models import Student, StudentStatus, TokenSequence
from apps.queue.services import call_next, check_in, close_centre
from tests.queue.helpers import data, live_centre, post, raw_student

pytestmark = pytest.mark.django_db(transaction=True)


def race(n, fn):
    """Run fn(i) in n threads released together. Returns [("ok", value) | ("err", exc)]."""
    barrier = threading.Barrier(n)
    results: list = [None] * n

    def worker(i):
        try:
            barrier.wait(timeout=10)
            results[i] = ("ok", fn(i))
        except Exception as exc:  # noqa: BLE001 - collected for assertions
            results[i] = ("err", exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert all(not t.is_alive() for t in threads), "a racing thread hung (deadlock?)"
    return results


def test_cq19_concurrent_check_ins_get_distinct_tokens_and_balanced_load():
    centre = live_centre()
    a = post(centre, "A", ["PCM"], "Desk 1").counsellor
    b = post(centre, "B", ["PCM"], "Desk 2").counsellor
    n = 10
    results = race(n, lambda i: check_in(centre, data(mobile=f"98000000{i:02d}"), "self").token)
    assert [r[0] for r in results] == ["ok"] * n, results
    tokens = sorted(r[1] for r in results)
    assert tokens == sorted(f"PCM-{i:02d}" for i in range(1, n + 1))
    assert TokenSequence.objects.get(centre=centre).last_number == n
    loads = Counter(Student.objects.filter(centre=centre).values_list("counsellor_id", flat=True))
    assert loads == {a.id: n // 2, b.id: n // 2}  # lowest load each time -> even split


def test_cq20_same_mobile_race_gives_one_token_and_one_duplicate():
    centre = live_centre()
    post(centre, "A", ["PCM"], "Desk 1")
    results = race(2, lambda i: check_in(centre, data(mobile="9811022001"), "self"))
    oks = [r for r in results if r[0] == "ok"]
    errs = [r[1] for r in results if r[0] == "err"]
    assert len(oks) == 1 and len(errs) == 1 and isinstance(errs[0], DuplicateToken), results
    assert errs[0].existing.token == oks[0][1].token
    assert Student.objects.filter(centre=centre, mobile="9811022001").count() == 1
    assert TokenSequence.objects.get(centre=centre).last_number == 1


def test_cq39_concurrent_call_next_on_one_desk_never_leaves_two_called():
    centre = live_centre()
    c = post(centre, "A", ["PCM"], "Desk 1").counsellor
    raw_student(centre, c, "PCM-01")
    raw_student(centre, c, "PCM-02")
    results = race(2, lambda i: call_next(c, centre=centre).student.token)
    oks = [r for r in results if r[0] == "ok"]
    errs = [r[1] for r in results if r[0] == "err"]
    assert len(oks) == 1 and len(errs) == 1 and isinstance(errs[0], DeskBusy), results
    assert Student.objects.filter(counsellor=c, status=StudentStatus.CALLED).count() == 1


def test_cq8_concurrent_close_and_check_ins_issue_no_token_after_close():
    centre = live_centre()
    post(centre, "A", ["PCM"], "Desk 1")
    n = 6  # thread 0 closes, the rest check in

    def act(i):
        if i == 0:
            return close_centre(centre)
        return check_in(centre, data(mobile=f"98100000{i:02d}"), "self").token

    results = race(n, act)
    close_result = results[0]
    assert close_result[0] == "ok", results
    checkins = results[1:]
    issued = [r[1] for r in checkins if r[0] == "ok"]
    refused = [r[1] for r in checkins if r[0] == "err"]
    assert all(isinstance(e, CentreNotLive) for e in refused), refused
    assert Centre.objects.get(pk=centre.pk).status == CentreStatus.CLOSED
    students = Student.objects.filter(centre=centre)
    # Every token issued before the close was swept to not_counselled; none is left waiting.
    assert sorted(students.values_list("token", flat=True)) == sorted(issued)
    assert set(students.values_list("status", flat=True)) <= {StudentStatus.NOT_COUNSELLED}
    assert close_result[1] == len(issued)
    assert TokenSequence.objects.get(centre=centre).last_number == len(issued)


def test_cq8_concurrent_double_close_counts_once():
    centre = live_centre()
    c = post(centre, "A", ["PCM"], "Desk 1").counsellor
    raw_student(centre, c, "PCM-01")
    results = race(2, lambda i: close_centre(centre))
    oks = [r[1] for r in results if r[0] == "ok"]
    errs = [r[1] for r in results if r[0] == "err"]
    assert oks == [1] and len(errs) == 1 and isinstance(errs[0], CloseRefused), results
