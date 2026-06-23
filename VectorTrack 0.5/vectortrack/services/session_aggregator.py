"""Merge Vectorworks log sessions, DB sessions, adjustments, and exclusions."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, List, Optional, Sequence, Set

from vectortrack.log_parser import (
    SessionRecord,
    parse_sessions_for_aliases,
    read_log_content,
)
from vectortrack.services.alias_resolver import AliasResolver

if TYPE_CHECKING:
    from vectortrack.db.repository import Repository

MACHINES_DIR = "machines"
LOCAL_MACHINE_ID = "local"


@dataclass
class UnifiedSession:
    start: datetime
    end: datetime
    hours: float
    machine_id: str
    source: str
    file_path: str
    file_alias: str
    project_id: str
    hourly_rate: float = 0.0
    session_id: Optional[int] = None
    adjustment_id: Optional[int] = None
    log_key: Optional[str] = None
    exclusion_id: Optional[int] = None
    is_open: bool = False
    is_editable: bool = False
    is_excluded: bool = False
    conflict_ids: List[str] = field(default_factory=list)
    notes: str = ""
    uid: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def amount(self) -> float:
        return round(self.hours * self.hourly_rate, 2)

    @property
    def status(self) -> str:
        if self.is_excluded:
            return "Excluded"
        if self.conflict_ids:
            return "Conflict"
        if self.is_open:
            return "Open"
        return "Closed"


@dataclass
class ConflictGroup:
    id: str
    session_ids: List[str]
    message: str


def normalize_file_name(value: str) -> str:
    return os.path.basename((value or "").replace("\\", "/")).strip().lower()


def machine_id_from_log_path(log_path: str) -> str:
    parts = log_path.replace("\\", "/").split("/")
    if MACHINES_DIR in parts:
        index = parts.index(MACHINES_DIR)
        if index + 1 < len(parts):
            return parts[index + 1]
    return LOCAL_MACHINE_ID


def make_log_key(
    start: datetime,
    end: datetime,
    file_alias: str,
    machine_id: str,
) -> str:
    return "|".join(
        [
            start.isoformat(),
            end.isoformat(),
            normalize_file_name(file_alias),
            machine_id or LOCAL_MACHINE_ID,
        ]
    )


def _sessions_overlap(left: UnifiedSession, right: UnifiedSession) -> bool:
    if normalize_file_name(left.file_alias) != normalize_file_name(right.file_alias):
        return False
    if left.machine_id == right.machine_id:
        return False
    start_a = left.start
    end_a = left.end
    start_b = right.start
    end_b = right.end
    return start_a < end_b and start_b < end_a


class SessionAggregator:
    def __init__(self, repository: Repository, alias_resolver: Optional[AliasResolver] = None):
        self.repository = repository
        self.alias_resolver = alias_resolver or AliasResolver()

    def sessions_for_file(
        self,
        file_path: str,
        log_paths: Sequence[str],
        project_id: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> List[UnifiedSession]:
        file_alias = Path(file_path).name
        project = project_id or Path(file_path).stem
        aliases = self._aliases_for_names([file_alias, project])
        sessions = self._collect_sessions(
            aliases=aliases,
            log_paths=log_paths,
            project_filter=project,
            file_filter=file_path,
            now=now,
        )
        return self._finalize(sessions)

    def sessions_for_project(
        self,
        project_code: str,
        log_paths: Sequence[str],
        assigned_files: Optional[dict[str, str]] = None,
        now: Optional[datetime] = None,
    ) -> List[UnifiedSession]:
        aliases = self._aliases_for_project(project_code, assigned_files=assigned_files)
        sessions = self._collect_sessions(
            aliases=aliases,
            log_paths=log_paths,
            project_filter=project_code,
            file_filter=None,
            now=now,
        )
        return self._finalize(sessions)

    def detect_conflicts(self, sessions: Sequence[UnifiedSession]) -> List[ConflictGroup]:
        groups: List[ConflictGroup] = []
        active = [session for session in sessions if not session.is_excluded]
        seen_pairs: Set[tuple[str, str]] = set()

        for index, left in enumerate(active):
            members = {left.uid}
            for right in active[index + 1 :]:
                if not _sessions_overlap(left, right):
                    continue
                pair = tuple(sorted((left.uid, right.uid)))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                members.add(right.uid)
                left.conflict_ids.append(right.uid)
                right.conflict_ids.append(left.uid)

            if len(members) > 1:
                group_id = str(uuid.uuid4())
                message = (
                    f"Overlapping sessions on {left.file_alias} "
                    f"({left.machine_id} vs other machines)"
                )
                groups.append(
                    ConflictGroup(
                        id=group_id,
                        session_ids=sorted(members),
                        message=message,
                    )
                )
                for session in active:
                    if session.uid in members:
                        if group_id not in session.conflict_ids:
                            session.conflict_ids.append(group_id)
        return groups

    def _aliases_for_project(
        self,
        project_code: str,
        assigned_files: Optional[dict[str, str]] = None,
    ) -> List[str]:
        aliases: Set[str] = {project_code}
        project = self.repository.get_project_by_code(project_code)
        if project:
            for rule in self.repository.list_alias_rules(project_id=project.id, active_only=True):
                aliases.add(rule.alias_pattern)

        for row in self.repository.list_sessions(project_id=project_code, include_open=True, limit=15000):
            if row.file_alias:
                aliases.add(row.file_alias)
            if row.file_path:
                aliases.add(Path(row.file_path).name)

        if assigned_files:
            for file_path, code in assigned_files.items():
                if code == project_code:
                    aliases.add(Path(file_path).name)
                    aliases.add(Path(file_path).stem)

        return self._expand_log_aliases(aliases)

    def _expand_log_aliases(self, names: Iterable[str]) -> List[str]:
        expanded: Set[str] = set()
        stems: Set[str] = set()

        for name in names:
            if not name:
                continue
            base = os.path.basename(name.replace("\\", "/")).strip()
            expanded.add(base)
            expanded.add(base if base.lower().endswith(".vwx") else f"{base}.vwx")
            stem = Path(base).stem if base.lower().endswith(".vwx") else base
            expanded.add(stem)
            stems.add(stem.lower())
            expanded.add(f"{stem} v2026.vwx")
            expanded.add(f"{stem} v2.vwx")
            expanded.add(f"{stem} v2")
            match = self.alias_resolver.resolve(base)
            if match:
                expanded.add(match.canonical)

        for stem in sorted(stems):
            expanded.add(f"{stem} v2.vwx")
            expanded.add(f"{stem} v2")
            if stem.endswith(" v2"):
                base = stem[:-3].strip()
                if base:
                    expanded.add(base)
                    expanded.add(f"{base}.vwx")

        return sorted({item for item in expanded if item})

    def _aliases_for_names(self, names: Iterable[str]) -> List[str]:
        aliases: Set[str] = set()
        for name in names:
            if name:
                aliases.add(name)
                match = self.alias_resolver.resolve(name)
                if match:
                    aliases.add(match.canonical)
        return self._expand_log_aliases(aliases)

    def _collect_sessions(
        self,
        aliases: Sequence[str],
        log_paths: Sequence[str],
        project_filter: str,
        file_filter: Optional[str],
        now: Optional[datetime],
    ) -> List[UnifiedSession]:
        if now is None:
            now = datetime.now()

        unified: List[UnifiedSession] = []
        unified.extend(
            self._log_sessions(
                aliases=aliases,
                log_paths=log_paths,
                project_filter=project_filter,
                file_filter=file_filter,
                now=now,
            )
        )
        unified.extend(
            self._db_sessions(
                project_filter=project_filter,
                file_filter=file_filter,
            )
        )
        unified.extend(
            self._adjustment_sessions(
                project_filter=project_filter,
                file_filter=file_filter,
            )
        )
        return self._apply_exclusions(unified)

    def _log_sessions(
        self,
        aliases: Sequence[str],
        log_paths: Sequence[str],
        project_filter: str,
        file_filter: Optional[str],
        now: datetime,
    ) -> List[UnifiedSession]:
        sessions: List[UnifiedSession] = []
        alias_list = self._expand_log_aliases(list(aliases) or [project_filter])

        for log_path in log_paths:
            if not os.path.isfile(log_path):
                continue
            machine_id = machine_id_from_log_path(log_path)
            try:
                content = read_log_content(log_path)
            except OSError:
                continue

            parsed = parse_sessions_for_aliases(content, alias_list, now=now)
            for alias, (records, _total) in parsed.items():
                file_alias = Path(alias).name
                if not file_alias.lower().endswith(".vwx"):
                    file_alias = f"{file_alias}.vwx"
                if file_filter and normalize_file_name(file_filter) != normalize_file_name(file_alias):
                    if normalize_file_name(Path(file_filter).name) != normalize_file_name(file_alias):
                        continue
                rate = self.repository._hourly_rate_for_project(project_filter)
                for record in records:
                    log_key = make_log_key(record.start, record.end, file_alias, machine_id)
                    sessions.append(
                        UnifiedSession(
                            start=record.start,
                            end=record.end,
                            hours=record.hours,
                            machine_id=machine_id,
                            source="log",
                            file_path=file_filter or file_alias,
                            file_alias=file_alias,
                            project_id=project_filter,
                            hourly_rate=rate,
                            log_key=log_key,
                            is_open=record.is_open,
                            is_editable=True,
                        )
                    )
        return self._dedupe_log_sessions(sessions)

    def _db_sessions(
        self,
        project_filter: str,
        file_filter: Optional[str],
    ) -> List[UnifiedSession]:
        rows = self.repository.list_sessions(project_id=project_filter, include_open=True, limit=15000)
        sessions: List[UnifiedSession] = []
        for row in rows:
            if file_filter and normalize_file_name(row.file_path) != normalize_file_name(file_filter):
                continue
            hours = row.active_duration.total_seconds() / 3600.0
            end_time = row.end_time or row.start_time
            source = row.source or "live"
            sessions.append(
                UnifiedSession(
                    start=row.start_time,
                    end=end_time,
                    hours=hours,
                    machine_id=row.machine_id or LOCAL_MACHINE_ID,
                    source=source,
                    file_path=row.file_path,
                    file_alias=row.file_alias or Path(row.file_path).name,
                    project_id=row.project_id,
                    hourly_rate=row.hourly_rate,
                    session_id=row.id,
                    is_open=row.end_time is None,
                    is_editable=source in {"live", "manual"},
                )
            )
        return sessions

    def _adjustment_sessions(
        self,
        project_filter: str,
        file_filter: Optional[str],
    ) -> List[UnifiedSession]:
        sessions: List[UnifiedSession] = []
        for row in self.repository.list_adjustments(project_id=project_filter):
            if file_filter and normalize_file_name(str(row["file_path"])) != normalize_file_name(file_filter):
                continue
            start = datetime.fromisoformat(str(row["start_time"]))
            end = datetime.fromisoformat(str(row["end_time"]))
            hours = max(0.0, (end - start).total_seconds() / 3600.0)
            sessions.append(
                UnifiedSession(
                    start=start,
                    end=end,
                    hours=hours,
                    machine_id=str(row.get("machine_id") or LOCAL_MACHINE_ID),
                    source="adjustment",
                    file_path=str(row["file_path"]),
                    file_alias=Path(str(row["file_path"])).name,
                    project_id=str(row["project_id"]),
                    hourly_rate=float(row.get("hourly_rate") or 0.0),
                    adjustment_id=int(row["id"]),
                    log_key=str(row.get("replaces_log_key") or "") or None,
                    is_editable=True,
                    notes=str(row.get("notes") or ""),
                )
            )
        return sessions

    def _apply_exclusions(self, sessions: List[UnifiedSession]) -> List[UnifiedSession]:
        exclusions = self.repository.list_exclusions()
        exclusion_by_key = {
            str(row.get("log_key") or ""): int(row["id"])
            for row in exclusions
            if row.get("log_key")
        }
        for session in sessions:
            if session.log_key and session.log_key in exclusion_by_key:
                session.is_excluded = True
                session.exclusion_id = exclusion_by_key[session.log_key]
        return sessions

    def _dedupe_log_sessions(self, sessions: List[UnifiedSession]) -> List[UnifiedSession]:
        seen: Set[str] = set()
        deduped: List[UnifiedSession] = []
        for session in sorted(sessions, key=lambda item: item.start):
            if not session.log_key:
                deduped.append(session)
                continue
            if session.log_key in seen:
                continue
            seen.add(session.log_key)
            deduped.append(session)
        return deduped

    def _finalize(self, sessions: List[UnifiedSession]) -> List[UnifiedSession]:
        sessions = self._suppress_log_duplicates(sessions)
        visible = [session for session in sessions if not session.is_excluded]
        self.detect_conflicts(visible)
        return sorted(sessions, key=lambda item: item.start, reverse=True)

    def _suppress_log_duplicates(self, sessions: List[UnifiedSession]) -> List[UnifiedSession]:
        db_signatures = {
            (
                session.start.isoformat(),
                (session.end.isoformat() if session.end else ""),
                normalize_file_name(session.file_alias),
            )
            for session in sessions
            if session.source in {"live", "manual"} and session.session_id is not None
        }
        filtered: List[UnifiedSession] = []
        for session in sessions:
            if session.source != "log":
                filtered.append(session)
                continue
            signature = (
                session.start.isoformat(),
                session.end.isoformat(),
                normalize_file_name(session.file_alias),
            )
            if signature in db_signatures:
                continue
            filtered.append(session)
        return filtered
