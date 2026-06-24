"""Resolve hourly billing rates for projects and sessions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from vectortrack.db.repository import Repository


def resolve_rate(
    project_id: str,
    *,
    default_rate: float,
    project_hourly_rate: Optional[float] = None,
    override_rate: Optional[float] = None,
) -> float:
    """Return the effective hourly rate for a session write."""
    if override_rate is not None:
        return float(override_rate)
    if not project_id:
        return float(default_rate)
    if project_hourly_rate is not None:
        return float(project_hourly_rate)
    return float(default_rate)


def resolve_rate_for_project(
    repository: Repository,
    project_id: str,
    *,
    override_rate: Optional[float] = None,
) -> float:
    """Look up project rate via repository, falling back to the default rate."""
    project_rate: Optional[float] = None
    if project_id:
        project = repository.get_project_by_code(project_id)
        if project is not None:
            project_rate = float(project.hourly_rate)
    return resolve_rate(
        project_id,
        default_rate=float(repository.default_hourly_rate),
        project_hourly_rate=project_rate,
        override_rate=override_rate,
    )
