"""Settings guard rails."""

import importlib

import pytest
from django.core.exceptions import ImproperlyConfigured


def test_the_stub_otp_code_is_refused_outside_debug(monkeypatch):
    monkeypatch.setenv("DEBUG", "False")
    monkeypatch.setenv("OTP_STUB_CODE", "1234")
    import config.settings.base as base

    with pytest.raises(ImproperlyConfigured):
        importlib.reload(base)
    monkeypatch.setenv("DEBUG", "True")
    importlib.reload(base)  # restore a valid module for the rest of the run
