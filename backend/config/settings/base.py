"""Base settings shared by every environment. Values come from backend/.env."""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
    MESSAGING_STUB_FAIL_TO=(list, []),
    OTP_TTL_MIN=(int, 10),
    OTP_RESEND_SEC=(int, 30),
    OTP_MAX_ATTEMPTS=(int, 5),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

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

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["OPTIONS"] = {
    "charset": "utf8mb4",
    "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
}
DATABASES["default"]["TEST"] = {
    "NAME": "test_counselqueue",
    "CHARSET": "utf8mb4",
    "COLLATION": "utf8mb4_unicode_ci",
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
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

# --- DRF / JWT ------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "apps.common.exceptions.exception_handler",
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
MESSAGING_PROVIDER = env("MESSAGING_PROVIDER", default="apps.messaging.providers.stub.StubProvider")
MESSAGING_STUB_FAIL_TO = env("MESSAGING_STUB_FAIL_TO")

# --- OTP (CQ-18) ----------------------------------------------------------
OTP_TTL_MIN = env("OTP_TTL_MIN")
OTP_RESEND_SEC = env("OTP_RESEND_SEC")
OTP_MAX_ATTEMPTS = env("OTP_MAX_ATTEMPTS")
OTP_STUB_CODE = env("OTP_STUB_CODE", default="")

# --- seed_demo (non-DEBUG passwords come only from env) -------------------
SEED_ADMIN_PASSWORD = env("SEED_ADMIN_PASSWORD", default="")
SEED_STAFF_PASSWORD = env("SEED_STAFF_PASSWORD", default="")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"apps": {"handlers": ["console"], "level": "INFO"}},
}
