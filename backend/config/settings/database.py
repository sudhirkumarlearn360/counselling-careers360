"""MySQL aliases configured the same way as cnext-backend-deb (MASTER_DB_* / SLAVE_DB_*)."""

from __future__ import annotations

import os
from typing import Any

MYSQL_OPTIONS = {"charset": "utf8mb4", "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"}


def mysql_alias(prefix: str, test: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build one DATABASES entry from `{prefix}_NAME/USER/PASSWORD/HOST` environment variables."""
    return {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv(f"{prefix}_NAME", ""),
        "USER": os.getenv(f"{prefix}_USER", ""),
        "PASSWORD": os.getenv(f"{prefix}_PASSWORD", ""),
        "HOST": os.getenv(f"{prefix}_HOST", ""),
        "PORT": "3306",
        "CONN_MAX_AGE": 60,
        "OPTIONS": dict(MYSQL_OPTIONS),
        "TEST": dict(test or {}),
    }
