"""Test settings: same MySQL server, database `test_counselqueue`."""

from .base import *  # noqa: F401,F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MESSAGING_PROVIDER = "apps.messaging.providers.stub.StubProvider"
MESSAGING_STUB_FAIL_TO = []
FRONTEND_BASE_URL = "http://localhost:5173"
OTP_STUB_CODE = "1234"
SEED_ADMIN_PASSWORD = ""
SEED_STAFF_PASSWORD = ""
