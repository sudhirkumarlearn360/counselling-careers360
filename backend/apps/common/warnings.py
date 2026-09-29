"""Non-blocking warnings returned beside a successful write: ``{"data": ..., "warnings": [...]}``."""

from __future__ import annotations


def warning(code: str, message: str) -> dict:
    return {"code": code, "message": message}
