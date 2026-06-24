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


def project_display_name(name: str, code: str = "") -> str:
    """Prefer the human-readable project name in UI labels."""
    cleaned_name = name.strip()
    cleaned_code = code.strip()
    return cleaned_name or cleaned_code


def project_report_label(name: str, code: str = "") -> str:
    """Format project number and name for reports and paperwork exports."""
    cleaned_name = name.strip()
    cleaned_code = code.strip()
    if not cleaned_code or cleaned_code == cleaned_name:
        return cleaned_name or cleaned_code
    if not cleaned_name:
        return cleaned_code
    return f"{cleaned_code} — {cleaned_name}"


def resolve_project_code(name: str, code: str = "") -> str:
    """Return the stored project key; code is optional and falls back to name."""
    cleaned_name = name.strip()
    cleaned_code = code.strip()
    if not cleaned_name:
        return ""
    return cleaned_code or cleaned_name
