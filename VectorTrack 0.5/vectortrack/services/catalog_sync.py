"""Shared clients/projects catalog sync via catalog.json in the sync folder."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from enum import Enum
from typing import TYPE_CHECKING, Any

from vectortrack.budget import BudgetType, ProjectBudget, load_project_budget, save_project_budget
from vectortrack.models import AliasRule, BillableProject, Client
from vectortrack.sync_folder import catalog_path, parse_updated_at, read_json_file, write_catalog_json

if TYPE_CHECKING:
    from vectortrack.db.repository import Repository

CATALOG_VERSION = 1
FUZZY_CLIENT_THRESHOLD = 0.85


class CatalogItemKind(str, Enum):
    CLIENT = "client"
    PROJECT = "project"


class CatalogItemStatus(str, Enum):
    IN_SYNC = "in_sync"
    REMOTE_ONLY = "remote_only"
    LOCAL_ONLY = "local_only"
    CONFLICT = "conflict"
    SUGGESTED_DUPLICATE = "suggested_duplicate"


class CatalogApplyMode(str, Enum):
    IMPORT_REMOTE = "import_remote"
    USE_REMOTE = "use_remote"
    MERGE_CLIENT = "merge_client"
    IMPORT_AS_NEW_CLIENT = "import_as_new_client"
    KEEP_LOCAL = "keep_local"
    DISMISS = "dismiss"


@dataclass
class CatalogViewRow:
    kind: CatalogItemKind
    key: str
    status: CatalogItemStatus
    local: dict[str, Any] | None = None
    remote: dict[str, Any] | None = None
    similarity: float | None = None
    suggested_local_key: str | None = None
    field_diffs: list[str] = field(default_factory=list)

    @property
    def row_id(self) -> str:
        if self.status == CatalogItemStatus.SUGGESTED_DUPLICATE and self.suggested_local_key:
            return f"{self.kind.value}:suggest:{self.key}:{self.suggested_local_key}"
        return f"{self.kind.value}:{self.key}"

    @property
    def needs_review(self) -> bool:
        return self.status in {
            CatalogItemStatus.REMOTE_ONLY,
            CatalogItemStatus.CONFLICT,
            CatalogItemStatus.SUGGESTED_DUPLICATE,
        }


@dataclass
class CatalogDiffResult:
    rows: list[CatalogViewRow] = field(default_factory=list)

    @property
    def suggestion_count(self) -> int:
        return sum(1 for row in self.rows if row.status == CatalogItemStatus.SUGGESTED_DUPLICATE)

    @property
    def remote_only_count(self) -> int:
        return sum(1 for row in self.rows if row.status == CatalogItemStatus.REMOTE_ONLY)

    @property
    def conflict_count(self) -> int:
        return sum(1 for row in self.rows if row.status == CatalogItemStatus.CONFLICT)

    @property
    def pending_review_count(self) -> int:
        return sum(1 for row in self.rows if row.needs_review)


@dataclass
class CatalogApplyAction:
    row: CatalogViewRow
    mode: CatalogApplyMode


@dataclass
class CatalogApplySummary:
    clients_added: int = 0
    clients_updated: int = 0
    projects_added: int = 0
    projects_updated: int = 0
    fuzzy_merged: list[tuple[str, str]] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(
            self.clients_added
            or self.clients_updated
            or self.projects_added
            or self.projects_updated
            or self.fuzzy_merged
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_client_name(name: str) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip().lower())


def client_key_for_values(name: str, code: str | None) -> str:
    normalized_code = str(code or "").strip()
    if normalized_code:
        return normalized_code
    slug = normalize_client_name(name)
    return slug or "unnamed"


def client_key(client: Client) -> str:
    return client_key_for_values(client.name, client.code)


def _empty_catalog() -> dict[str, Any]:
    return {
        "version": CATALOG_VERSION,
        "updated_at": _now_iso(),
        "clients": {},
        "projects": {},
    }


def _budget_to_dict(budget: ProjectBudget) -> dict[str, Any]:
    return {"type": budget.budget_type.value, "amount": float(budget.amount)}


def _budget_from_dict(raw: object) -> ProjectBudget:
    if not isinstance(raw, dict):
        return ProjectBudget(BudgetType.NONE, 0.0)
    raw_type = str(raw.get("type") or BudgetType.NONE.value).strip().lower()
    amount = float(raw.get("amount") or 0.0)
    if raw_type == BudgetType.MONEY.value and amount > 0:
        return ProjectBudget(BudgetType.MONEY, amount)
    if raw_type == BudgetType.HOURS.value and amount > 0:
        return ProjectBudget(BudgetType.HOURS, amount)
    return ProjectBudget(BudgetType.NONE, 0.0)


def _alias_to_dict(rule: AliasRule) -> dict[str, Any]:
    return {
        "pattern": rule.alias_pattern,
        "is_regex": bool(rule.is_regex),
        "priority": int(rule.priority),
        "is_active": bool(rule.is_active),
    }


def export_local_catalog(repository: Repository) -> dict[str, Any]:
    clients: dict[str, dict[str, Any]] = {}
    for client in repository.list_clients(active_only=False):
        key = client_key(client)
        clients[key] = {
            "name": client.name,
            "code": client.code,
            "is_active": bool(client.is_active),
            "updated_at": client.updated_at or _now_iso(),
        }

    projects: dict[str, dict[str, Any]] = {}
    for project in repository.list_projects(active_only=False):
        client = repository.get_client(project.client_id)
        resolved_client_key = client_key(client) if client else "default"
        aliases: list[dict[str, Any]] = []
        if project.id is not None:
            for rule in repository.list_alias_rules(project_id=project.id, active_only=False):
                aliases.append(_alias_to_dict(rule))

        projects[project.project_code] = {
            "client_key": resolved_client_key,
            "project_code": project.project_code,
            "name": project.name,
            "hourly_rate": float(project.hourly_rate),
            "is_active": bool(project.is_active),
            "is_locked": bool(project.is_locked),
            "locked_at": project.locked_at,
            "invoice_number": project.invoice_number,
            "budget": _budget_to_dict(load_project_budget(repository, project.project_code)),
            "aliases": aliases,
            "updated_at": project.updated_at or _now_iso(),
        }

    return {
        "version": CATALOG_VERSION,
        "updated_at": _now_iso(),
        "clients": clients,
        "projects": projects,
    }


def _pick_entity(
    local_entity: dict[str, Any] | None,
    remote_entity: dict[str, Any] | None,
    *,
    local_wins_tie: bool,
) -> dict[str, Any] | None:
    if local_entity is None:
        return dict(remote_entity) if remote_entity is not None else None
    if remote_entity is None:
        return dict(local_entity)

    local_ts = parse_updated_at(local_entity.get("updated_at"))
    remote_ts = parse_updated_at(remote_entity.get("updated_at"))
    if local_ts > remote_ts:
        return dict(local_entity)
    if remote_ts > local_ts:
        return dict(remote_entity)
    return dict(local_entity) if local_wins_tie else dict(remote_entity)


def merge_catalogs(
    local: dict[str, Any],
    remote: dict[str, Any],
    *,
    local_wins_tie: bool = True,
) -> dict[str, Any]:
    local_clients = local.get("clients") if isinstance(local.get("clients"), dict) else {}
    remote_clients = remote.get("clients") if isinstance(remote.get("clients"), dict) else {}
    local_projects = local.get("projects") if isinstance(local.get("projects"), dict) else {}
    remote_projects = remote.get("projects") if isinstance(remote.get("projects"), dict) else {}

    merged_clients: dict[str, dict[str, Any]] = {}
    for key in sorted(set(local_clients) | set(remote_clients)):
        picked = _pick_entity(
            local_clients.get(key),
            remote_clients.get(key),
            local_wins_tie=local_wins_tie,
        )
        if picked is not None:
            merged_clients[key] = picked

    merged_projects: dict[str, dict[str, Any]] = {}
    for key in sorted(set(local_projects) | set(remote_projects)):
        picked = _pick_entity(
            local_projects.get(key),
            remote_projects.get(key),
            local_wins_tie=local_wins_tie,
        )
        if picked is not None:
            merged_projects[key] = picked

    local_ts = parse_updated_at(local.get("updated_at"))
    remote_ts = parse_updated_at(remote.get("updated_at"))
    if local_ts >= remote_ts or local_wins_tie:
        updated_at = local.get("updated_at") or _now_iso()
    else:
        updated_at = remote.get("updated_at") or _now_iso()

    return {
        "version": CATALOG_VERSION,
        "updated_at": updated_at,
        "clients": merged_clients,
        "projects": merged_projects,
    }


def _find_client_by_key(repository: Repository, key: str) -> Client | None:
    normalized = str(key or "").strip()
    if not normalized:
        return None
    for client in repository.list_clients(active_only=False):
        if client_key(client) == normalized:
            return client
    return repository.find_client_by_code(normalized)


def _find_similar_client(repository: Repository, name: str) -> Client | None:
    target = normalize_client_name(name)
    if not target:
        return None
    best: Client | None = None
    best_ratio = 0.0
    for client in repository.list_clients(active_only=False):
        ratio = SequenceMatcher(None, target, normalize_client_name(client.name)).ratio()
        if ratio >= FUZZY_CLIENT_THRESHOLD and ratio > best_ratio:
            best = client
            best_ratio = ratio
    return best


def _should_apply_remote(remote_entity: dict[str, Any], local_updated_at: str | None) -> bool:
    remote_ts = parse_updated_at(remote_entity.get("updated_at"))
    local_ts = parse_updated_at(local_updated_at)
    return remote_ts > local_ts


def _apply_client_entity(
    repository: Repository,
    remote_key: str,
    remote_client: dict[str, Any],
    summary: CatalogApplySummary,
    key_map: dict[str, str],
    *,
    fuzzy_merge: bool,
    force: bool = False,
) -> None:
    name = str(remote_client.get("name") or "").strip()
    code = str(remote_client.get("code") or "").strip() or None
    if not name:
        return

    existing = _find_client_by_key(repository, remote_key)
    if existing is None and code:
        existing = repository.find_client_by_code(code)
    if existing is None and fuzzy_merge:
        similar = _find_similar_client(repository, name)
        if similar is not None:
            summary.fuzzy_merged.append((name, similar.name))
            existing = similar

    if existing is None:
        created = repository.create_client(
            Client(
                name=name,
                code=code,
                is_active=bool(remote_client.get("is_active", True)),
                updated_at=str(remote_client.get("updated_at") or _now_iso()),
            )
        )
        key_map[remote_key] = client_key(created)
        summary.clients_added += 1
        return

    key_map[remote_key] = client_key(existing)
    if not force and not _should_apply_remote(remote_client, existing.updated_at):
        return

    repository.update_client(
        Client(
            id=existing.id,
            name=name,
            code=code or existing.code,
            is_active=bool(remote_client.get("is_active", existing.is_active)),
            created_at=existing.created_at,
            updated_at=str(remote_client.get("updated_at") or _now_iso()),
        )
    )
    summary.clients_updated += 1


def _resolve_client_id(repository: Repository, client_key_value: str, key_map: dict[str, str]) -> int:
    resolved_key = key_map.get(client_key_value, client_key_value)
    client = _find_client_by_key(repository, resolved_key)
    if client is None or client.id is None:
        default = repository.find_client_by_normalized_name("Default")
        if default is None:
            default = repository.create_client(Client(name="Default"))
        return default.id or 0
    return client.id


def _sync_aliases(
    repository: Repository,
    project_id: int,
    remote_aliases: list[dict[str, Any]],
) -> None:
    remote_patterns = {
        str(item.get("pattern") or "").strip()
        for item in remote_aliases
        if isinstance(item, dict) and str(item.get("pattern") or "").strip()
    }
    existing_rules = repository.list_alias_rules(project_id=project_id, active_only=False)
    existing_by_pattern = {rule.alias_pattern: rule for rule in existing_rules}

    for item in remote_aliases:
        if not isinstance(item, dict):
            continue
        pattern = str(item.get("pattern") or "").strip()
        if not pattern:
            continue
        existing = existing_by_pattern.get(pattern)
        repository.upsert_alias_rule(
            AliasRule(
                id=existing.id if existing else None,
                project_id=project_id,
                alias_pattern=pattern,
                is_regex=bool(item.get("is_regex", False)),
                priority=int(item.get("priority", 100)),
                is_active=bool(item.get("is_active", True)),
                created_at=existing.created_at if existing else None,
            )
        )

    for rule in existing_rules:
        if rule.alias_pattern not in remote_patterns and rule.is_active:
            repository.upsert_alias_rule(
                AliasRule(
                    id=rule.id,
                    project_id=project_id,
                    alias_pattern=rule.alias_pattern,
                    is_regex=rule.is_regex,
                    priority=rule.priority,
                    is_active=False,
                    created_at=rule.created_at,
                )
            )


def _apply_project_entity(
    repository: Repository,
    remote_project: dict[str, Any],
    summary: CatalogApplySummary,
    key_map: dict[str, str],
    *,
    force: bool = False,
) -> None:
    project_code = str(remote_project.get("project_code") or "").strip()
    if not project_code:
        return

    name = str(remote_project.get("name") or project_code).strip()
    client_id = _resolve_client_id(
        repository,
        str(remote_project.get("client_key") or "default"),
        key_map,
    )
    budget = _budget_from_dict(remote_project.get("budget"))
    aliases = remote_project.get("aliases")
    alias_items = aliases if isinstance(aliases, list) else []

    existing = repository.get_project_by_code(project_code)
    if existing is None:
        created = repository.create_project(
            BillableProject(
                client_id=client_id,
                project_code=project_code,
                name=name,
                hourly_rate=float(remote_project.get("hourly_rate") or repository.default_hourly_rate),
                is_active=bool(remote_project.get("is_active", True)),
                is_locked=bool(remote_project.get("is_locked", False)),
                locked_at=remote_project.get("locked_at"),
                invoice_number=remote_project.get("invoice_number"),
                updated_at=str(remote_project.get("updated_at") or _now_iso()),
            )
        )
        save_project_budget(repository, project_code, budget)
        if created.id is not None:
            _sync_aliases(repository, created.id, alias_items)
        summary.projects_added += 1
        return

    if not force and not _should_apply_remote(remote_project, existing.updated_at):
        return

    if existing.is_locked:
        repository.set_project_lock(
            project_code,
            locked=bool(remote_project.get("is_locked", existing.is_locked)),
            invoice_number=remote_project.get("invoice_number"),
        )
        save_project_budget(repository, project_code, budget)
        if existing.id is not None:
            _sync_aliases(repository, existing.id, alias_items)
        summary.projects_updated += 1
        return

    repository.update_project(
        BillableProject(
            id=existing.id,
            client_id=client_id,
            project_code=project_code,
            name=name,
            hourly_rate=float(remote_project.get("hourly_rate") or existing.hourly_rate),
            is_active=bool(remote_project.get("is_active", existing.is_active)),
            is_locked=bool(remote_project.get("is_locked", existing.is_locked)),
            locked_at=remote_project.get("locked_at"),
            invoice_number=remote_project.get("invoice_number"),
            created_at=existing.created_at,
            updated_at=str(remote_project.get("updated_at") or _now_iso()),
        )
    )
    save_project_budget(repository, project_code, budget)
    if existing.id is not None:
        _sync_aliases(repository, existing.id, alias_items)
    summary.projects_updated += 1


def apply_catalog_to_local(
    repository: Repository,
    catalog: dict[str, Any],
    *,
    fuzzy_merge: bool = False,
) -> CatalogApplySummary:
    summary = CatalogApplySummary()
    clients = catalog.get("clients") if isinstance(catalog.get("clients"), dict) else {}
    projects = catalog.get("projects") if isinstance(catalog.get("projects"), dict) else {}
    key_map: dict[str, str] = {}

    for remote_key, remote_client in clients.items():
        if isinstance(remote_client, dict):
            _apply_client_entity(
                repository,
                str(remote_key),
                remote_client,
                summary,
                key_map,
                fuzzy_merge=fuzzy_merge,
            )

    for _project_key, remote_project in projects.items():
        if isinstance(remote_project, dict):
            _apply_project_entity(repository, remote_project, summary, key_map)

    return summary


def _dismissal_setting_key(kind: str, remote_key: str, local_key: str) -> str:
    return f"catalog_dismissed:{kind}:{remote_key}:{local_key}"


def is_suggestion_dismissed(
    repository: Repository,
    kind: str,
    remote_key: str,
    local_key: str,
    remote_updated_at: str | None,
) -> bool:
    stored = repository.get_setting(_dismissal_setting_key(kind, remote_key, local_key))
    if not stored:
        return False
    return stored == str(remote_updated_at or "")


def dismiss_suggestion(
    repository: Repository,
    kind: str,
    remote_key: str,
    local_key: str,
    remote_updated_at: str | None,
) -> None:
    repository.set_setting(
        _dismissal_setting_key(kind, remote_key, local_key),
        str(remote_updated_at or ""),
    )


def _client_snapshots_equal(local: dict[str, Any], remote: dict[str, Any]) -> bool:
    return (
        normalize_client_name(str(local.get("name") or ""))
        == normalize_client_name(str(remote.get("name") or ""))
        and str(local.get("code") or "").strip() == str(remote.get("code") or "").strip()
        and bool(local.get("is_active", True)) == bool(remote.get("is_active", True))
    )


def _client_field_diffs(local: dict[str, Any], remote: dict[str, Any]) -> list[str]:
    diffs: list[str] = []
    if normalize_client_name(str(local.get("name") or "")) != normalize_client_name(
        str(remote.get("name") or "")
    ):
        diffs.append("name")
    if str(local.get("code") or "").strip() != str(remote.get("code") or "").strip():
        diffs.append("code")
    if bool(local.get("is_active", True)) != bool(remote.get("is_active", True)):
        diffs.append("is_active")
    return diffs


def _project_snapshots_equal(local: dict[str, Any], remote: dict[str, Any]) -> bool:
    local_budget = _budget_from_dict(local.get("budget"))
    remote_budget = _budget_from_dict(remote.get("budget"))
    return (
        str(local.get("name") or "").strip() == str(remote.get("name") or "").strip()
        and float(local.get("hourly_rate") or 0.0) == float(remote.get("hourly_rate") or 0.0)
        and str(local.get("client_key") or "") == str(remote.get("client_key") or "")
        and bool(local.get("is_active", True)) == bool(remote.get("is_active", True))
        and local_budget == remote_budget
    )


def _project_field_diffs(local: dict[str, Any], remote: dict[str, Any]) -> list[str]:
    diffs: list[str] = []
    if str(local.get("name") or "").strip() != str(remote.get("name") or "").strip():
        diffs.append("name")
    if float(local.get("hourly_rate") or 0.0) != float(remote.get("hourly_rate") or 0.0):
        diffs.append("rate")
    if str(local.get("client_key") or "") != str(remote.get("client_key") or ""):
        diffs.append("client")
    if bool(local.get("is_active", True)) != bool(remote.get("is_active", True)):
        diffs.append("is_active")
    local_budget = _budget_from_dict(local.get("budget"))
    remote_budget = _budget_from_dict(remote.get("budget"))
    if local_budget != remote_budget:
        diffs.append("budget")
    return diffs


def _similarity_ratio(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_client_name(left), normalize_client_name(right)).ratio()


def find_suggested_duplicates(
    repository: Repository,
    catalog: dict[str, Any],
    *,
    local: dict[str, Any] | None = None,
) -> list[CatalogViewRow]:
    local = local or export_local_catalog(repository)
    local_clients = local.get("clients") if isinstance(local.get("clients"), dict) else {}
    remote_clients = catalog.get("clients") if isinstance(catalog.get("clients"), dict) else {}
    suggestions: list[CatalogViewRow] = []

    for remote_key, remote_client in remote_clients.items():
        if not isinstance(remote_client, dict):
            continue
        remote_key_str = str(remote_key)
        if remote_key_str in local_clients:
            continue
        remote_code = str(remote_client.get("code") or "").strip()
        if remote_code and any(
            isinstance(item, dict) and str(item.get("code") or "").strip() == remote_code
            for item in local_clients.values()
        ):
            continue

        remote_name = str(remote_client.get("name") or "")
        best_local_key: str | None = None
        best_ratio = 0.0
        for local_key, local_client in local_clients.items():
            if not isinstance(local_client, dict):
                continue
            ratio = _similarity_ratio(remote_name, str(local_client.get("name") or ""))
            if ratio >= FUZZY_CLIENT_THRESHOLD and ratio > best_ratio:
                best_local_key = str(local_key)
                best_ratio = ratio

        if best_local_key is None:
            continue
        if is_suggestion_dismissed(
            repository,
            CatalogItemKind.CLIENT.value,
            remote_key_str,
            best_local_key,
            str(remote_client.get("updated_at") or ""),
        ):
            continue

        suggestions.append(
            CatalogViewRow(
                kind=CatalogItemKind.CLIENT,
                key=remote_key_str,
                status=CatalogItemStatus.SUGGESTED_DUPLICATE,
                local=local_clients.get(best_local_key),
                remote=remote_client,
                similarity=best_ratio,
                suggested_local_key=best_local_key,
                field_diffs=_client_field_diffs(
                    local_clients.get(best_local_key) or {},
                    remote_client,
                ),
            )
        )

    local_projects = local.get("projects") if isinstance(local.get("projects"), dict) else {}
    remote_projects = catalog.get("projects") if isinstance(catalog.get("projects"), dict) else {}
    for remote_key, remote_project in remote_projects.items():
        if not isinstance(remote_project, dict):
            continue
        remote_key_str = str(remote_key)
        if remote_key_str in local_projects:
            continue
        remote_name = str(remote_project.get("name") or "")
        best_local_key: str | None = None
        best_ratio = 0.0
        for local_key, local_project in local_projects.items():
            if not isinstance(local_project, dict):
                continue
            ratio = _similarity_ratio(remote_name, str(local_project.get("name") or ""))
            if ratio >= FUZZY_CLIENT_THRESHOLD and ratio > best_ratio:
                best_local_key = str(local_key)
                best_ratio = ratio
        if best_local_key is None or best_ratio < FUZZY_CLIENT_THRESHOLD:
            continue
        dismiss_key = f"name:{best_local_key}"
        if is_suggestion_dismissed(
            repository,
            CatalogItemKind.PROJECT.value,
            remote_key_str,
            dismiss_key,
            str(remote_project.get("updated_at") or ""),
        ):
            continue
        suggestions.append(
            CatalogViewRow(
                kind=CatalogItemKind.PROJECT,
                key=remote_key_str,
                status=CatalogItemStatus.SUGGESTED_DUPLICATE,
                local=local_projects.get(best_local_key),
                remote=remote_project,
                similarity=best_ratio,
                suggested_local_key=best_local_key,
                field_diffs=_project_field_diffs(
                    local_projects.get(best_local_key) or {},
                    remote_project,
                ),
            )
        )

    return suggestions


def build_catalog_view(repository: Repository, catalog: dict[str, Any]) -> CatalogDiffResult:
    local = export_local_catalog(repository)
    local_clients = local.get("clients") if isinstance(local.get("clients"), dict) else {}
    remote_clients = catalog.get("clients") if isinstance(catalog.get("clients"), dict) else {}
    local_projects = local.get("projects") if isinstance(local.get("projects"), dict) else {}
    remote_projects = catalog.get("projects") if isinstance(catalog.get("projects"), dict) else {}

    suggestions = find_suggested_duplicates(repository, catalog, local=local)
    suggested_client_keys = {
        row.key for row in suggestions if row.kind == CatalogItemKind.CLIENT
    }
    suggested_project_keys = {
        row.key for row in suggestions if row.kind == CatalogItemKind.PROJECT
    }

    rows: list[CatalogViewRow] = []

    for key in sorted(set(local_clients) | set(remote_clients)):
        local_item = local_clients.get(key) if isinstance(local_clients.get(key), dict) else None
        remote_item = remote_clients.get(key) if isinstance(remote_clients.get(key), dict) else None
        if local_item is not None and remote_item is not None:
            if _client_snapshots_equal(local_item, remote_item):
                status = CatalogItemStatus.IN_SYNC
            else:
                status = CatalogItemStatus.CONFLICT
            rows.append(
                CatalogViewRow(
                    kind=CatalogItemKind.CLIENT,
                    key=str(key),
                    status=status,
                    local=local_item,
                    remote=remote_item,
                    field_diffs=_client_field_diffs(local_item, remote_item)
                    if status == CatalogItemStatus.CONFLICT
                    else [],
                )
            )
        elif local_item is not None:
            rows.append(
                CatalogViewRow(
                    kind=CatalogItemKind.CLIENT,
                    key=str(key),
                    status=CatalogItemStatus.LOCAL_ONLY,
                    local=local_item,
                )
            )
        elif remote_item is not None and str(key) not in suggested_client_keys:
            rows.append(
                CatalogViewRow(
                    kind=CatalogItemKind.CLIENT,
                    key=str(key),
                    status=CatalogItemStatus.REMOTE_ONLY,
                    remote=remote_item,
                )
            )

    for key in sorted(set(local_projects) | set(remote_projects)):
        local_item = local_projects.get(key) if isinstance(local_projects.get(key), dict) else None
        remote_item = remote_projects.get(key) if isinstance(remote_projects.get(key), dict) else None
        if local_item is not None and remote_item is not None:
            if _project_snapshots_equal(local_item, remote_item):
                status = CatalogItemStatus.IN_SYNC
            else:
                status = CatalogItemStatus.CONFLICT
            rows.append(
                CatalogViewRow(
                    kind=CatalogItemKind.PROJECT,
                    key=str(key),
                    status=status,
                    local=local_item,
                    remote=remote_item,
                    field_diffs=_project_field_diffs(local_item, remote_item)
                    if status == CatalogItemStatus.CONFLICT
                    else [],
                )
            )
        elif local_item is not None:
            rows.append(
                CatalogViewRow(
                    kind=CatalogItemKind.PROJECT,
                    key=str(key),
                    status=CatalogItemStatus.LOCAL_ONLY,
                    local=local_item,
                )
            )
        elif remote_item is not None and str(key) not in suggested_project_keys:
            rows.append(
                CatalogViewRow(
                    kind=CatalogItemKind.PROJECT,
                    key=str(key),
                    status=CatalogItemStatus.REMOTE_ONLY,
                    remote=remote_item,
                )
            )

    rows.extend(suggestions)
    return CatalogDiffResult(rows=rows)


def _force_apply_client(
    repository: Repository,
    remote_key: str,
    remote_client: dict[str, Any],
    summary: CatalogApplySummary,
    key_map: dict[str, str],
    *,
    fuzzy_merge: bool,
    target_local_key: str | None = None,
) -> None:
    if target_local_key:
        existing = _find_client_by_key(repository, target_local_key)
        if existing is not None:
            key_map[remote_key] = client_key(existing)
            repository.update_client(
                Client(
                    id=existing.id,
                    name=str(remote_client.get("name") or existing.name),
                    code=str(remote_client.get("code") or "").strip() or existing.code,
                    is_active=bool(remote_client.get("is_active", existing.is_active)),
                    created_at=existing.created_at,
                    updated_at=str(remote_client.get("updated_at") or _now_iso()),
                )
            )
            summary.clients_updated += 1
            summary.fuzzy_merged.append(
                (str(remote_client.get("name") or ""), existing.name)
            )
            return
    _apply_client_entity(
        repository,
        remote_key,
        remote_client,
        summary,
        key_map,
        fuzzy_merge=fuzzy_merge,
    )


def apply_catalog_rows(
    repository: Repository,
    catalog: dict[str, Any],
    actions: list[CatalogApplyAction],
) -> CatalogApplySummary:
    summary = CatalogApplySummary()
    key_map: dict[str, str] = {}
    clients = catalog.get("clients") if isinstance(catalog.get("clients"), dict) else {}
    projects = catalog.get("projects") if isinstance(catalog.get("projects"), dict) else {}

    for item in actions:
        row = item.row
        if item.mode == CatalogApplyMode.KEEP_LOCAL:
            continue
        if item.mode == CatalogApplyMode.DISMISS:
            dismiss_suggestion(
                repository,
                row.kind.value,
                row.key,
                row.suggested_local_key or row.key,
                str((row.remote or {}).get("updated_at") or ""),
            )
            continue

        if row.kind == CatalogItemKind.CLIENT:
            remote_client = row.remote
            if not isinstance(remote_client, dict):
                continue
            if item.mode == CatalogApplyMode.IMPORT_AS_NEW_CLIENT:
                _apply_client_entity(
                    repository,
                    row.key,
                    remote_client,
                    summary,
                    key_map,
                    fuzzy_merge=False,
                )
            elif item.mode == CatalogApplyMode.IMPORT_REMOTE:
                _apply_client_entity(
                    repository,
                    row.key,
                    remote_client,
                    summary,
                    key_map,
                    fuzzy_merge=False,
                    force=True,
                )
            elif item.mode == CatalogApplyMode.USE_REMOTE:
                _apply_client_entity(
                    repository,
                    row.key,
                    remote_client,
                    summary,
                    key_map,
                    fuzzy_merge=False,
                    force=True,
                )
            elif item.mode == CatalogApplyMode.MERGE_CLIENT:
                _force_apply_client(
                    repository,
                    row.key,
                    remote_client,
                    summary,
                    key_map,
                    fuzzy_merge=True,
                    target_local_key=row.suggested_local_key,
                )
            continue

        remote_project = row.remote
        if not isinstance(remote_project, dict):
            if row.key in projects:
                remote_project = projects[row.key]
            else:
                continue
        force = item.mode == CatalogApplyMode.USE_REMOTE
        if item.mode in {CatalogApplyMode.IMPORT_REMOTE, CatalogApplyMode.USE_REMOTE}:
            _apply_project_entity(repository, remote_project, summary, key_map, force=force)

    return summary


def import_remote_project(
    repository: Repository,
    catalog: dict[str, Any],
    project_code: str,
) -> CatalogApplySummary:
    projects = catalog.get("projects") if isinstance(catalog.get("projects"), dict) else {}
    remote_project = projects.get(project_code)
    if not isinstance(remote_project, dict):
        return CatalogApplySummary()
    clients = catalog.get("clients") if isinstance(catalog.get("clients"), dict) else {}
    actions: list[CatalogApplyAction] = []
    client_key_value = str(remote_project.get("client_key") or "")
    remote_client = clients.get(client_key_value)
    if isinstance(remote_client, dict) and _find_client_by_key(repository, client_key_value) is None:
        actions.append(
            CatalogApplyAction(
                row=CatalogViewRow(
                    kind=CatalogItemKind.CLIENT,
                    key=client_key_value,
                    status=CatalogItemStatus.REMOTE_ONLY,
                    remote=remote_client,
                ),
                mode=CatalogApplyMode.IMPORT_REMOTE,
            )
        )
    actions.append(
        CatalogApplyAction(
            row=CatalogViewRow(
                kind=CatalogItemKind.PROJECT,
                key=project_code,
                status=CatalogItemStatus.REMOTE_ONLY,
                remote=remote_project,
            ),
            mode=CatalogApplyMode.IMPORT_REMOTE,
        )
    )
    return apply_catalog_rows(repository, catalog, actions)


def catalog_has_project_code(catalog: dict[str, Any], project_code: str) -> bool:
    projects = catalog.get("projects") if isinstance(catalog.get("projects"), dict) else {}
    return str(project_code).strip() in projects


def filter_orphan_project_codes(
    project_codes: list[str],
    catalog: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Return (stub_codes, catalog_only_codes)."""
    stub_codes: list[str] = []
    catalog_only: list[str] = []
    for code in project_codes:
        normalized = str(code).strip()
        if not normalized:
            continue
        if catalog_has_project_code(catalog, normalized):
            catalog_only.append(normalized)
        else:
            stub_codes.append(normalized)
    return stub_codes, catalog_only


def read_catalog(sync_folder: str) -> dict[str, Any]:
    path = catalog_path(sync_folder)
    if not os.path.isfile(path):
        return _empty_catalog()
    payload = read_json_file(path)
    if not payload:
        return _empty_catalog()
    return payload


def pull_catalog(sync_folder: str, repository: Repository) -> CatalogApplySummary | None:
    """Explicit full apply (tests/legacy). Review UI should use apply_catalog_rows instead."""
    if not sync_folder or not os.path.isdir(sync_folder):
        return None
    path = catalog_path(sync_folder)
    if not os.path.isfile(path):
        return CatalogApplySummary()
    payload = read_json_file(path)
    if not payload:
        return CatalogApplySummary()
    return apply_catalog_to_local(repository, payload, fuzzy_merge=False)


def push_catalog(
    sync_folder: str,
    repository: Repository,
    local_catalog: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    if not sync_folder:
        return False, "Sync not configured"
    try:
        os.makedirs(sync_folder, exist_ok=True)
        local = local_catalog or export_local_catalog(repository)
        remote = read_catalog(sync_folder)
        merged = merge_catalogs(local, remote, local_wins_tie=True)
        merged["updated_at"] = _now_iso()
        write_catalog_json(catalog_path(sync_folder), merged)
        return True, ""
    except OSError as exc:
        return False, str(exc)


def sync_catalog(sync_folder: str, repository: Repository) -> tuple[CatalogApplySummary | None, bool, str]:
    ok, err = push_catalog(sync_folder, repository)
    return None, ok, err
