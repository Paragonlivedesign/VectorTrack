"""Vectorworks Log.txt parsing shared by desktop and plug-in."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Set, Tuple

LOG_FILENAME = "Vectorworks Log.txt"
YEAR_MIN = 2020
YEAR_MAX = 2030

VW_LOG_TIME_PREFERENCE_HELP = (
    'In Vectorworks, open Preferences and select the Session tab. '
    'Turn on "Log time in program". Vectorworks only creates Vectorworks Log.txt '
    "after this option is enabled — it is usually off on a new install."
)

VW_EVENT_RE = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2}\s+[AP]M)\s+"
    r'(Opened|Closed)\s+"([^"]+)"',
    re.IGNORECASE,
)
OPENED_LEGACY_RE = re.compile(
    r'Opened\s+"([^"]+)"[^\d]*(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)',
    re.IGNORECASE,
)
CLOSED_LEGACY_RE = re.compile(
    r'Closed\s+"([^"]+)"[^\d]*(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)',
    re.IGNORECASE,
)
SAVE_AS_RE = re.compile(
    r'(?:Save(?:d)?(?:\s+a\s+Copy)?(?:\s+As)?|Saved(?:\s+as)?)\s+"([^"]+)"'
    r'(?:\s+(?:from|as)\s+"([^"]+)")?',
    re.IGNORECASE,
)
TIMESTAMP_FMT = "%m/%d/%Y %I:%M:%S %p"


@dataclass
class SessionRecord:
    start: datetime
    end: datetime
    hours: float
    is_open: bool = False

    @property
    def duration_hours(self) -> float:
        return self.hours


def normalize_project_name(name: str) -> str:
    basename = os.path.basename((name or "").replace("\\", "/")).strip().lower()
    if basename.endswith(".vwx"):
        basename = basename[:-4]
    return basename


def _names_match(log_name: str, project_name: str) -> bool:
    return normalize_project_name(log_name) == normalize_project_name(project_name)


def _parse_timestamp(text: str) -> datetime:
    normalized = re.sub(r"\s+", " ", text.strip())
    return datetime.strptime(normalized, TIMESTAMP_FMT)


def _parse_log_event(line: str) -> Optional[Tuple[str, datetime, str]]:
    stripped = line.strip()
    if not stripped:
        return None

    native = VW_EVENT_RE.match(stripped)
    if native:
        timestamp = _parse_timestamp(f"{native.group(1)} {native.group(2)}")
        action = "open" if native.group(3).lower() == "opened" else "close"
        return action, timestamp, native.group(4)

    open_match = OPENED_LEGACY_RE.search(stripped)
    if open_match:
        return "open", _parse_timestamp(open_match.group(2)), open_match.group(1)

    close_match = CLOSED_LEGACY_RE.search(stripped)
    if close_match:
        return "close", _parse_timestamp(close_match.group(2)), close_match.group(1)

    return None


def _parse_save_as_alias(line: str) -> Optional[Tuple[str, Optional[str]]]:
    stripped = line.strip()
    if not stripped:
        return None
    match = SAVE_AS_RE.search(stripped)
    if not match:
        return None
    return match.group(1), match.group(2)


def extract_year_from_vw_exe(exe_path: str) -> Optional[int]:
    if not exe_path:
        return None
    base = os.path.basename(exe_path)
    for year in range(YEAR_MAX, YEAR_MIN - 1, -1):
        if str(year) in base:
            return year
    parent = os.path.basename(os.path.dirname(exe_path))
    if parent.isdigit() and YEAR_MIN <= int(parent) <= YEAR_MAX:
        return int(parent)
    return None


def _roaming_root() -> str:
    return os.path.join(
        os.path.expanduser("~"), "AppData", "Roaming", "Nemetschek", "Vectorworks"
    )


def vectorworks_log_roaming_dir() -> str:
    return _roaming_root()


def find_all_log_paths() -> List[str]:
    root = _roaming_root()
    if not os.path.isdir(root):
        return []

    paths: List[str] = []
    for year in range(YEAR_MAX, YEAR_MIN - 1, -1):
        candidate = os.path.join(root, str(year), LOG_FILENAME)
        if os.path.isfile(candidate):
            paths.append(candidate)
    return paths


def find_log_path(preferred_year: Optional[int] = None) -> Optional[str]:
    paths = find_all_log_paths()
    if not paths:
        return None
    if preferred_year is not None:
        preferred = expected_log_path_for_year(preferred_year)
        if os.path.isfile(preferred):
            return preferred
    return paths[0]


def expected_log_path_for_year(year: int) -> str:
    return os.path.join(_roaming_root(), str(year), LOG_FILENAME)


def expected_log_path_for_exe(vw_exe_path: str) -> Optional[str]:
    year = extract_year_from_vw_exe(vw_exe_path)
    if year is None:
        return None
    return expected_log_path_for_year(year)


def resolve_log_paths(
    vw_exe_path: Optional[str] = None,
    manual_log_path: Optional[str] = None,
    merge_other_years: bool = True,
) -> Tuple[List[str], str]:
    all_paths = find_all_log_paths()
    if not all_paths:
        return [], "No Vectorworks logs found"

    if manual_log_path:
        manual = os.path.normpath(manual_log_path)
        if not os.path.isfile(manual):
            return [], f"Log not found: {manual}"
        paths = [manual]
        desc = f"Manual: {manual}"
        if merge_other_years:
            for path in all_paths:
                if os.path.normpath(path) != manual and path not in paths:
                    paths.append(path)
            desc += " (+ older years)"
        return paths, desc

    year = extract_year_from_vw_exe(vw_exe_path or "")
    primary = find_log_path(year)
    if not primary:
        return all_paths, "Auto: newest available log"

    paths = [primary]
    year_label = os.path.basename(os.path.dirname(primary))
    exe_name = os.path.basename(vw_exe_path) if vw_exe_path else "Vectorworks"
    desc = f"Auto: {year_label} (from {exe_name})"
    if merge_other_years:
        for path in all_paths:
            if path != primary:
                paths.append(path)
        desc += " (+ older years)"
    return paths, desc


def read_log_content(log_path: str) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(log_path, "r", encoding=encoding, errors="replace") as handle:
                return handle.read()
        except OSError:
            continue
    raise OSError(f"Unable to read log file: {log_path}")


def _apply_save_as_line(
    save_alias: Tuple[str, Optional[str]],
    tracked_norms: Set[str],
    canonical_for_norm: Dict[str, str],
    open_start_by_norm: Dict[str, datetime],
) -> None:
    new_name, old_name = save_alias
    new_norm = normalize_project_name(new_name)
    old_norm = normalize_project_name(old_name) if old_name else None
    if old_norm and old_norm in tracked_norms and new_norm not in tracked_norms:
        tracked_norms.add(new_norm)
        canonical_for_norm[new_norm] = canonical_for_norm[old_norm]
    if old_norm and old_norm in open_start_by_norm:
        open_start_by_norm[new_norm] = open_start_by_norm.pop(old_norm)
        tracked_norms.add(new_norm)
        if new_norm not in canonical_for_norm:
            canonical_for_norm[new_norm] = canonical_for_norm.get(old_norm, new_name)


def parse_sessions_for_aliases(
    content: str,
    project_names: Sequence[str],
    now: Optional[datetime] = None,
) -> Dict[str, Tuple[List[SessionRecord], float]]:
    if now is None:
        now = datetime.now()

    requested = [name for name in project_names if str(name).strip()]
    if not requested:
        return {}

    tracked_norms: Set[str] = {normalize_project_name(name) for name in requested}
    canonical_for_norm: Dict[str, str] = {
        normalize_project_name(name): name for name in requested
    }
    sessions_by_name: Dict[str, List[SessionRecord]] = {name: [] for name in requested}
    totals_by_name: Dict[str, float] = {name: 0.0 for name in requested}
    open_start_by_norm: Dict[str, datetime] = {}

    for line in content.splitlines():
        save_alias = _parse_save_as_alias(line)
        if save_alias:
            _apply_save_as_line(
                save_alias, tracked_norms, canonical_for_norm, open_start_by_norm
            )

        event = _parse_log_event(line)
        if not event:
            continue

        action, timestamp, log_name = event
        log_norm = normalize_project_name(log_name)
        if log_norm not in tracked_norms:
            continue

        if action == "open":
            open_start_by_norm[log_norm] = timestamp
            continue

        if action == "close" and log_norm in open_start_by_norm:
            session_start = open_start_by_norm.pop(log_norm)
            hours = max(0.0, (timestamp - session_start).total_seconds() / 3600)
            canonical_name = canonical_for_norm[log_norm]
            sessions_by_name[canonical_name].append(
                SessionRecord(start=session_start, end=timestamp, hours=hours)
            )
            totals_by_name[canonical_name] += hours

    for log_norm, session_start in open_start_by_norm.items():
        canonical_name = canonical_for_norm[log_norm]
        hours = max(0.0, (now - session_start).total_seconds() / 3600)
        sessions_by_name[canonical_name].append(
            SessionRecord(start=session_start, end=now, hours=hours, is_open=True)
        )
        totals_by_name[canonical_name] += hours

    return {name: (sessions_by_name[name], totals_by_name[name]) for name in requested}


def parse_sessions(
    content: str,
    project_name: str,
    aliases: Optional[Sequence[str]] = None,
    now: Optional[datetime] = None,
) -> Tuple[List[SessionRecord], float]:
    alias_list = [project_name, *(aliases or [])]
    parsed = parse_sessions_for_aliases(content, alias_list, now=now)
    all_sessions: List[SessionRecord] = []
    seen: Set[Tuple[str, str, float, bool]] = set()
    total = 0.0
    for name in alias_list:
        sessions, _hours = parsed.get(name, ([], 0.0))
        for session in sessions:
            key = (
                session.start.isoformat(),
                session.end.isoformat(),
                round(session.hours, 4),
                session.is_open,
            )
            if key in seen:
                continue
            seen.add(key)
            all_sessions.append(session)
            total += session.hours
    all_sessions.sort(key=lambda item: item.start)
    return all_sessions, total


def _format_event_line(action: str, timestamp: datetime, project_name: str) -> str:
    verb = "Opened" if action == "open" else "Closed"
    return f'{verb} "{project_name}" at {timestamp.strftime(TIMESTAMP_FMT)}'


def merge_log_contents(sources: Sequence[str]) -> str:
    if not sources:
        return ""
    if len(sources) == 1:
        return sources[0]

    seen_events: Set[Tuple[str, str, str]] = set()
    events: List[Tuple[datetime, str, str]] = []
    save_as_lines: List[str] = []
    seen_save_as: Set[Tuple[str, Optional[str]]] = set()

    for content in sources:
        for line in content.splitlines():
            save_alias = _parse_save_as_alias(line)
            if save_alias:
                key = (save_alias[0], save_alias[1])
                if key not in seen_save_as:
                    seen_save_as.add(key)
                    save_as_lines.append(line.strip())
                continue

            event = _parse_log_event(line)
            if not event:
                continue

            action, timestamp, log_name = event
            dedupe_key = (
                timestamp.isoformat(),
                action,
                normalize_project_name(log_name),
            )
            if dedupe_key in seen_events:
                continue
            seen_events.add(dedupe_key)
            events.append((timestamp, action, log_name))

    events.sort(key=lambda item: item[0])
    merged_lines = list(save_as_lines)
    merged_lines.extend(
        _format_event_line(action, timestamp, log_name)
        for timestamp, action, log_name in events
    )
    return "\n".join(merged_lines)


def parse_sessions_from_sources(
    sources: Sequence[str],
    project_name: str,
    aliases: Optional[Sequence[str]] = None,
    now: Optional[datetime] = None,
) -> Tuple[List[SessionRecord], float]:
    merged = merge_log_contents(sources)
    return parse_sessions(merged, project_name, aliases=aliases, now=now)


def get_total_log_hours_for_file(
    file_path: str,
    now: Optional[datetime] = None,
    include_open_session: bool = False,
    log_paths: Optional[List[str]] = None,
) -> Tuple[float, int, List[str]]:
    project_name = os.path.basename(file_path)
    total_hours = 0.0
    session_count = 0
    used_paths: List[str] = []

    for log_path in log_paths or find_all_log_paths():
        try:
            content = read_log_content(log_path)
        except OSError:
            continue
        sessions, hours = parse_sessions(content, project_name, now=now)
        if sessions and not include_open_session and sessions[-1].is_open:
            hours -= sessions[-1].hours
            sessions = sessions[:-1]
        if sessions:
            used_paths.append(log_path)
            total_hours += hours
            session_count += len(sessions)

    return total_hours, session_count, used_paths


@dataclass
class LogReconciliation:
    closed_hours: float
    current_open_hours: float
    total_log_hours: float
    session_count: int
    log_paths: List[str]

    @property
    def historical_hours(self) -> float:
        return self.closed_hours


def get_log_reconciliation(
    file_path: str,
    vt_live_hours: float = 0.0,
    now: Optional[datetime] = None,
    log_paths: Optional[List[str]] = None,
) -> LogReconciliation:
    project_name = os.path.basename(file_path)
    closed_hours = 0.0
    current_open_hours = 0.0
    session_count = 0
    used_paths: List[str] = []

    for log_path in log_paths or find_all_log_paths():
        try:
            content = read_log_content(log_path)
        except OSError:
            continue
        sessions, _ = parse_sessions(content, project_name, now=now)
        if not sessions:
            continue
        used_paths.append(log_path)
        for session in sessions:
            session_count += 1
            if session.is_open:
                current_open_hours += session.hours
            else:
                closed_hours += session.hours

    total_log_hours = closed_hours + current_open_hours
    return LogReconciliation(
        closed_hours=closed_hours,
        current_open_hours=current_open_hours,
        total_log_hours=total_log_hours,
        session_count=session_count,
        log_paths=used_paths,
    )


def get_balance_delta(reconciliation: LogReconciliation, vt_live_hours: float) -> float:
    return round(reconciliation.current_open_hours - vt_live_hours, 2)


def format_session_line(session: SessionRecord, index: int, total: int) -> str:
    if session.is_open and index == total:
        return (
            f"  Current: {session.start.strftime('%m/%d %I:%M %p')} - NOW "
            f"({session.hours:.2f} hrs)"
        )
    return (
        f"  {session.start.strftime('%m/%d %I:%M %p')} - "
        f"{session.end.strftime('%I:%M %p')} ({session.hours:.2f} hrs)"
    )


def build_summary_text(
    project_name: str,
    sessions: List[SessionRecord],
    total_hours: float,
    rate: float,
    client_name: str = "",
    budget_hours: Optional[float] = None,
    trust_note: str = "",
    max_sessions: int = 10,
) -> str:
    lines = [
        f"TIME TRACKING: {project_name}",
        "=" * 56,
        "",
    ]
    if client_name:
        lines.append(f"Client: {client_name}")
    if budget_hours is not None and budget_hours > 0:
        remaining = max(0.0, budget_hours - total_hours)
        lines.append(f"Budget: {budget_hours:.2f} hrs")
        lines.append(f"Budget Remaining: {remaining:.2f} hrs")
    if trust_note:
        lines.append(f"Log Trust: {trust_note}")
    lines.extend(["", "SESSIONS:"])

    display = sessions[-max_sessions:] if len(sessions) > max_sessions else sessions
    offset = len(sessions) - len(display)
    for i, session in enumerate(display, start=offset + 1):
        lines.append(format_session_line(session, i, len(sessions)))

    if len(sessions) > max_sessions:
        lines.append(f"  ... and {len(sessions) - max_sessions} more sessions")

    total_amount = total_hours * rate
    lines.extend(
        [
            "",
            "-" * 56,
            f"Total Hours: {total_hours:.2f}",
            f"Rate: ${rate:.2f}/hour",
            f"TOTAL AMOUNT: ${total_amount:.2f}",
            "-" * 56,
        ]
    )
    return "\n".join(lines)
