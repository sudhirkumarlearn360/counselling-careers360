"""The provider interface every WhatsApp backend implements (counselqueue-messaging)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

STATUSES = ("queued", "sent", "delivered", "failed")


@dataclass(frozen=True)
class SendResult:
    provider_id: str
    status: str  # one of STATUSES

    def __post_init__(self):
        if self.status not in STATUSES:
            raise ValueError(f"Unknown send status {self.status!r}")


class MessagingProvider(Protocol):
    def send(self, to: str, body: str) -> SendResult: ...
