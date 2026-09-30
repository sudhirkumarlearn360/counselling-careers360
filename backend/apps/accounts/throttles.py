"""Per-IP throttles for the unauthenticated auth endpoints (rates: REST_FRAMEWORK DEFAULT_THROTTLE_RATES)."""

from __future__ import annotations

from django.conf import settings
from rest_framework.throttling import ScopedRateThrottle


class SettingsScopedRateThrottle(ScopedRateThrottle):
    """ScopedRateThrottle that reads the rate at request time, so settings overrides take effect."""

    def get_rate(self):
        return settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].get(self.scope)
