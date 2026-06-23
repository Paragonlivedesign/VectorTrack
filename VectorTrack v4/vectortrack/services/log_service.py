"""Service layer for Vectorworks log mining."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional, Sequence, Tuple

from ..log_parser import (
    SessionRecord,
    parse_sessions,
    parse_sessions_for_aliases,
    read_log_content,
    resolve_log_paths,
)
from .alias_resolver import AliasResolver


@dataclass(frozen=True)
class LogSummary:
    project_name: str
    closed_hours: float
    open_hours: float
    session_count: int
    trust_score: float
    log_paths: List[str]

    @property
    def total_hours(self) -> float:
        return self.closed_hours + self.open_hours


class LogService:
    """High-level operations over one or more Vectorworks log files."""

    def __init__(self, alias_resolver: Optional[AliasResolver] = None):
        self.alias_resolver = alias_resolver or AliasResolver()

    def resolve_sources(
        self,
        vw_exe_path: Optional[str] = None,
        manual_log_path: Optional[str] = None,
        merge_other_years: bool = True,
        extra_paths: Optional[Iterable[str]] = None,
    ) -> Tuple[List[str], str]:
        paths, description = resolve_log_paths(
            vw_exe_path=vw_exe_path,
            manual_log_path=manual_log_path,
            merge_other_years=merge_other_years,
        )
        deduped: List[str] = []
        seen = set()
        for path in [*(paths or []), *(extra_paths or [])]:
            norm = os.path.normpath(path)
            if norm in seen:
                continue
            if os.path.isfile(norm):
                deduped.append(norm)
                seen.add(norm)
        return deduped, description

    def get_project_summary(
        self,
        project_name: str,
        log_paths: Sequence[str],
        aliases: Optional[Sequence[str]] = None,
        now: Optional[datetime] = None,
    ) -> LogSummary:
        if now is None:
            now = datetime.now()
        alias_list = self._build_alias_list(project_name, aliases)

        all_sessions: List[SessionRecord] = []
        used_paths: List[str] = []
        save_as_hits = 0

        for path in log_paths:
            if not os.path.isfile(path):
                continue
            try:
                content = read_log_content(path)
            except OSError:
                continue
            used_paths.append(path)
            if "save" in content.lower() and "as" in content.lower():
                save_as_hits += 1

            parsed = parse_sessions_for_aliases(content, alias_list, now=now)
            for _alias, (sessions, _hours) in parsed.items():
                all_sessions.extend(sessions)

        deduped_sessions = self._dedupe_sessions(all_sessions)
        closed_hours = sum(session.hours for session in deduped_sessions if not session.is_open)
        open_hours = sum(session.hours for session in deduped_sessions if session.is_open)
        trust = self._compute_trust_score(
            session_count=len(deduped_sessions),
            source_count=len(used_paths),
            alias_count=len(alias_list),
            save_as_hits=save_as_hits,
        )
        return LogSummary(
            project_name=project_name,
            closed_hours=closed_hours,
            open_hours=open_hours,
            session_count=len(deduped_sessions),
            trust_score=trust,
            log_paths=used_paths,
        )

    def closed_hours_for_project(
        self,
        project_name: str,
        log_paths: Sequence[str],
        aliases: Optional[Sequence[str]] = None,
        now: Optional[datetime] = None,
    ) -> float:
        summary = self.get_project_summary(
            project_name=project_name,
            log_paths=log_paths,
            aliases=aliases,
            now=now,
        )
        return summary.closed_hours

    @staticmethod
    def _dedupe_sessions(sessions: Iterable[SessionRecord]) -> List[SessionRecord]:
        deduped: List[SessionRecord] = []
        seen = set()
        for session in sorted(sessions, key=lambda item: (item.start, item.end, item.is_open)):
            key = (
                session.start.isoformat(),
                session.end.isoformat(),
                round(session.hours, 4),
                session.is_open,
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(session)
        return deduped

    def _build_alias_list(
        self,
        project_name: str,
        aliases: Optional[Sequence[str]],
    ) -> List[str]:
        combined = [project_name, *(aliases or [])]
        match = self.alias_resolver.resolve(project_name)
        if match:
            combined.append(match.canonical)
        # Keep order stable while removing duplicates.
        out: List[str] = []
        seen = set()
        for item in combined:
            normalized = AliasResolver.normalize_name(item)
            if not normalized or normalized in seen:
                continue
            out.append(item)
            seen.add(normalized)
            if not normalized.endswith(".vwx"):
                with_ext = f"{item}.vwx" if not item.lower().endswith(".vwx") else item
                ext_norm = AliasResolver.normalize_name(with_ext)
                if ext_norm not in seen:
                    out.append(with_ext)
                    seen.add(ext_norm)
        return out

    @staticmethod
    def _compute_trust_score(
        session_count: int,
        source_count: int,
        alias_count: int,
        save_as_hits: int,
    ) -> float:
        score = 0.0
        if session_count > 0:
            score += 0.45
        if source_count > 1:
            score += 0.2
        if alias_count > 1:
            score += 0.2
        if save_as_hits > 0:
            score += 0.15
        return round(min(1.0, score), 2)
