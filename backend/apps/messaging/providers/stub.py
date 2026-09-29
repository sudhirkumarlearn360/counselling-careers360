"""Console provider for local, demo and test use. Fails for numbers in MESSAGING_STUB_FAIL_TO."""

from __future__ import annotations

import logging
import uuid

from django.conf import settings

from apps.messaging.providers.base import SendResult

logger = logging.getLogger("apps.messaging.stub")


class StubProvider:
    def send(self, to: str, body: str) -> SendResult:
        provider_id = f"stub-{uuid.uuid4().hex[:16]}"
        failed = to in (getattr(settings, "MESSAGING_STUB_FAIL_TO", None) or [])
        status = "failed" if failed else "sent"
        logger.info("WhatsApp stub %s to %s: %s", status, to, body)
        return SendResult(provider_id=provider_id, status=status)
