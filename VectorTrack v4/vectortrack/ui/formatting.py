"""Display formatting helpers for durations."""

from __future__ import annotations


def format_timer_hours(hours: float) -> str:
    """Format hours as a live timer string (H:MM:SS or M:SS)."""
    total_seconds = max(0, int(round(hours * 3600)))
    hours_part, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours_part:
        return f"{hours_part}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_hours_compact(hours: float) -> str:
    return f"{hours:.2f}h"
