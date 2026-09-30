"""Base settings shared by every environment. Values come from backend/.env (python-dotenv)."""

import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# from config.settings.database import mysql_alias  # MySQL (disabled: SQLite for laptop setup)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name: str, default: str = "") -> list:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


SECRET_KEY = os.getenv("SECRET_KEY", "")
DEBUG = env_bool("DEBUG")
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")
APPEND_SLASH = False  # routes have no trailing slash (django-backend-conventions "API routes")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "apps.common",
    "apps.accounts",
    "apps.centres",
    "apps.counsellors",
    "apps.queue",
    "apps.messaging",
    "apps.insights",
    "apps.public",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Writes and locking reads use "default"; read-only report selectors may use "slave".
# --- MySQL (disabled; re-enable and remove the SQLite block below for production) ---
# DATABASES = {
#     "default": mysql_alias("MASTER_DB", test={"NAME": "test_counselqueue"}),
#     "slave": mysql_alias("SLAVE_DB", test={"MIRROR": "default"}),
# }

# --- SQLite (local / laptop setup). "slave" points at the same file as "default". ---
_SQLITE_PATH = BASE_DIR / os.getenv("SQLITE_NAME", "db.sqlite3")
DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": _SQLITE_PATH},
    "slave": {"ENGINE": "django.db.backends.sqlite3", "NAME": _SQLITE_PATH, "TEST": {"MIRROR": "default"}},
}

AUTH_USER_MODEL = "accounts.StaffUser"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- CORS -----------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")

# --- DRF / JWT ------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "apps.common.exceptions.exception_handler",
    "DEFAULT_THROTTLE_RATES": {"login": "10/min", "logout": "30/min", "checkin": "30/min", "otp": "20/min"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

# --- Sign-in (CQ-2) -------------------------------------------------------
LOGIN_HELPDESK_AFTER_FAILURES = 3

# --- Messaging (counselqueue-messaging) -----------------------------------
MESSAGING_PROVIDER = os.getenv("MESSAGING_PROVIDER", "apps.messaging.providers.stub.StubProvider")
MESSAGING_STUB_FAIL_TO = env_list("MESSAGING_STUB_FAIL_TO")
# The student's live token link in messages is f"{FRONTEND_BASE_URL}/t/{access_key}" (CQ-26).
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

# --- OTP (CQ-18) ----------------------------------------------------------
OTP_TTL_MIN = env_int("OTP_TTL_MIN", 10)
OTP_RESEND_SEC = env_int("OTP_RESEND_SEC", 30)
OTP_MAX_ATTEMPTS = env_int("OTP_MAX_ATTEMPTS", 5)
OTP_STUB_CODE = os.getenv("OTP_STUB_CODE", "")
if OTP_STUB_CODE and not DEBUG:  # a fixed code would let anyone verify any number
    raise ImproperlyConfigured("OTP_STUB_CODE must be empty unless DEBUG is on.")

# --- seed_demo (non-DEBUG passwords come only from env) -------------------
SEED_ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "")
SEED_STAFF_PASSWORD = os.getenv("SEED_STAFF_PASSWORD", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"apps": {"handlers": ["console"], "level": "INFO"}},
}

# Delivery-status webhook signature key (CQ-58). Empty = webhook disabled.
MESSAGING_WEBHOOK_SECRET = os.getenv("MESSAGING_WEBHOOK_SECRET", "")
