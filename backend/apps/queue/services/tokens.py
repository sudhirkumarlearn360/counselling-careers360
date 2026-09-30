"""STREAM-NN token numbering (CQ-19). One sequence per centre, shared across streams, never goes back."""

from __future__ import annotations

from apps.queue.services.locks import lock_sequence


def next_token(centre, stream: str) -> str:
    """Take the next number under the centre's TokenSequence row lock. Grows past 99 (`PCM-100`)."""
    seq = lock_sequence(centre.pk)
    seq.last_number += 1
    seq.save(update_fields=["last_number"])
    return f"{stream}-{seq.last_number:02d}"
