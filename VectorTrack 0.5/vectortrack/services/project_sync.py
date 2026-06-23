"""Register project codes that are in use but missing from the database."""

from __future__ import annotations

from typing import Iterable, List, TYPE_CHECKING

from vectortrack.models import BillableProject, Client

if TYPE_CHECKING:
    from vectortrack.db.repository import Repository


def sync_orphan_project_codes(
    repository: Repository,
    project_codes: Iterable[str],
    *,
    default_rate: float,
    default_client_name: str = "Default",
) -> List[str]:
    """
    Ensure each project code exists in billable_projects.

    Returns the list of codes that were newly created.
    """
    normalized = sorted({str(code).strip() for code in project_codes if str(code).strip()})
    if not normalized:
        return []

    created: List[str] = []
    clients = repository.list_clients(active_only=False)
    client = next((c for c in clients if c.name.lower() == default_client_name.lower()), None)
    if client is None:
        client = repository.create_client(Client(name=default_client_name))

    for code in normalized:
        if repository.get_project_by_code(code) is not None:
            continue
        repository.create_project(
            BillableProject(
                client_id=client.id or 0,
                project_code=code,
                name=code,
                hourly_rate=float(default_rate),
            )
        )
        created.append(code)
    return created
