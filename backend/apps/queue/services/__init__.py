"""Queue engine services: the only code allowed to change student status or queue order."""

from apps.queue.services.transitions import close_centre

__all__ = ["close_centre"]
