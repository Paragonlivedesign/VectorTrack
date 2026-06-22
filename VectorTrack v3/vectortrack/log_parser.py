"""
Parse Vectorworks Log.txt for historical file open/close sessions.
"""

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

LOG_FILENAME = 'Vectorworks Log.txt'
YEAR_MIN = 2020
YEAR_MAX = 2030

# Native Vectorworks log: "11/24/2025  6:38:53 PM \t Opened \"file.vwx\"."
VW_EVENT_RE = re.compile(
    r'^(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2}\s+[AP]M)\s+'
    r'(Opened|Closed)\s+"([^"]+)"',
    re.IGNORECASE,
)
# Legacy / simplified format used in tests: Opened "file" at 6/1/2025 9:00:00 AM
OPENED_LEGACY_RE = re.compile(
    r'Opened\s+"([^"]+)"[^\d]*(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)',
    re.IGNORECASE,
)
CLOSED_LEGACY_RE = re.compile(
    r'Closed\s+"([^"]+)"[^\d]*(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)',
    re.IGNORECASE,
)
# Vectorworks save-as / save-a-copy variants.
SAVE_AS_RE = re.compile(
    r'(?:Save(?:d)?(?:\s+a\s+Copy)?(?:\s+As)?|Saved(?:\s+as)?)\s+"([^"]+)"'
    r'(?:\s+(?:from|as)\s+"([^"]+)")?',
    re.IGNORECASE,
)
TIMESTAMP_FMT = '%m/%d/%Y %I:%M:%S %p'


@dataclass
class SessionRecord:
    start: datetime
    end: datetime
    hours: float
    is_open: bool = False


def _normalize_project_name(name: str) -> str:
    return os.path.basename(name.replace('\\', '/')).strip().lower()


def _names_match(log_name: str, project_name: str) -> bool:
    return _normalize_project_name(log_name) == _normalize_project_name(project_name)


def _parse_timestamp(text: str) -> datetime:
    normalized = re.sub(r'\s+', ' ', text.strip())
    return datetime.strptime(normalized, TIMESTAMP_FMT)


def _parse_log_event(line: str) -> Optional[Tuple[str, datetime, str]]:
    """
    Parse one log line into (action, timestamp, filename).
    action is 'open' or 'close'. Returns None if not an open/close event.
    """
    stripped = line.strip()
    if not stripped:
        return None

    native = VW_EVENT_RE.match(stripped)
    if native:
        timestamp = _parse_timestamp(f'{native.group(1)} {native.group(2)}')
        action = 'open' if native.group(3).lower() == 'opened' else 'close'
        return action, timestamp, native.group(4)

    open_match = OPENED_LEGACY_RE.search(stripped)
    if open_match:
        return 'open', _parse_timestamp(open_match.group(2)), open_match.group(1)

    close_match = CLOSED_LEGACY_RE.search(stripped)
    if close_match:
        return 'close', _parse_timestamp(close_match.group(2)), close_match.group(1)

    return None


def _parse_save_as_alias(line: str) -> Optional[Tuple[str, Optional[str]]]:
    """
    Parse save-as/save-copy lines into (new_name, old_name).
    old_name can be None when source file is not present in the log line.
    """
    stripped = line.strip()
    if not stripped:
        return None
    match = SAVE_AS_RE.search(stripped)
    if not match:
        return None
    return match.group(1), match.group(2)


def extract_year_from_vw_exe(exe_path: str) -> Optional[int]:
    """Infer Vectorworks version year from an executable path."""
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
    return os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Nemetschek', 'Vectorworks')


def find_all_log_paths() -> List[str]:
    """Return all Vectorworks Log.txt files found (newest year folders first)."""
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
        preferred = os.path.join(_roaming_root(), str(preferred_year), LOG_FILENAME)
        if os.path.isfile(preferred):
            return preferred
    return paths[0]


def resolve_log_paths(
    vw_exe_path: Optional[str] = None,
    manual_log_path: Optional[str] = None,
    merge_other_years: bool = True,
) -> Tuple[List[str], str]:
    """
    Resolve which Vectorworks Log.txt files to read.

    Manual path takes priority. Otherwise picks the log folder matching the
    Vectorworks executable year (e.g. Vectorworks2026.exe -> .../2026/...).
    """
    all_paths = find_all_log_paths()
    if not all_paths:
        return [], 'No Vectorworks logs found'

    if manual_log_path:
        manual = os.path.normpath(manual_log_path)
        if not os.path.isfile(manual):
            return [], f'Log not found: {manual}'
        paths = [manual]
        desc = f'Manual: {manual}'
        if merge_other_years:
            for path in all_paths:
                if os.path.normpath(path) != manual and path not in paths:
                    paths.append(path)
            desc += ' (+ older years)'
        return paths, desc

    year = extract_year_from_vw_exe(vw_exe_path or '')
    primary = find_log_path(year)
    if not primary:
        return all_paths, 'Auto: newest available log'

    paths = [primary]
    year_label = os.path.basename(os.path.dirname(primary))
    exe_name = os.path.basename(vw_exe_path) if vw_exe_path else 'Vectorworks'
    desc = f'Auto: {year_label} (from {exe_name})'
    if merge_other_years:
        for path in all_paths:
            if path != primary:
                paths.append(path)
        desc += ' (+ older years)'
    return paths, desc


def read_log_content(log_path: str) -> str:
    for encoding in ('utf-8', 'utf-8-sig', 'cp1252', 'latin-1'):
        try:
            with open(log_path, 'r', encoding=encoding, errors='replace') as handle:
                return handle.read()
        except OSError:
            continue
    raise OSError(f'Unable to read log file: {log_path}')


def parse_sessions(
    content: str,
    project_name: str,
    now: Optional[datetime] = None,
) -> Tuple[List[SessionRecord], float]:
    if now is None:
        now = datetime.now()

    sessions: List[SessionRecord] = []
    current_start: Optional[datetime] = None
    total_hours = 0.0

    for line in content.splitlines():
        event = _parse_log_event(line)
        if not event:
            continue

        action, timestamp, log_name = event
        if not _names_match(log_name, project_name):
            continue

        if action == 'open':
            current_start = timestamp
            continue

        if action == 'close' and current_start is not None:
            session_end = timestamp
            hours = max(0.0, (session_end - current_start).total_seconds() / 3600)
            sessions.append(SessionRecord(start=current_start, end=session_end, hours=hours))
            total_hours += hours
            current_start = None

    if current_start is not None:
        hours = max(0.0, (now - current_start).total_seconds() / 3600)
        sessions.append(
            SessionRecord(start=current_start, end=now, hours=hours, is_open=True)
        )
        total_hours += hours

    return sessions, total_hours


def parse_sessions_for_aliases(
    content: str,
    project_names: List[str],
    now: Optional[datetime] = None,
) -> Dict[str, Tuple[List[SessionRecord], float]]:
    """
    Parse sessions for multiple aliases in one pass.

    Returns a mapping keyed by each requested project name:
        {project_name: (sessions, total_hours)}

    Save-as lines are mined so newly-created filenames can be linked
    back to the active tracked project where the source filename is known.
    """
    if now is None:
        now = datetime.now()

    requested = [name for name in project_names if name]
    if not requested:
        return {}

    tracked_norms: Set[str] = {_normalize_project_name(name) for name in requested}
    canonical_for_norm: Dict[str, str] = {
        _normalize_project_name(name): name for name in requested
    }

    sessions_by_name: Dict[str, List[SessionRecord]] = {name: [] for name in requested}
    totals_by_name: Dict[str, float] = {name: 0.0 for name in requested}
    open_start_by_norm: Dict[str, datetime] = {}

    for line in content.splitlines():
        save_alias = _parse_save_as_alias(line)
        if save_alias:
            new_name, old_name = save_alias
            new_norm = _normalize_project_name(new_name)
            old_norm = _normalize_project_name(old_name) if old_name else None
            if old_norm and old_norm in tracked_norms and new_norm not in tracked_norms:
                tracked_norms.add(new_norm)
                canonical_for_norm[new_norm] = canonical_for_norm[old_norm]

        event = _parse_log_event(line)
        if not event:
            continue

        action, timestamp, log_name = event
        log_norm = _normalize_project_name(log_name)
        if log_norm not in tracked_norms:
            continue

        if action == 'open':
            open_start_by_norm[log_norm] = timestamp
            continue

        if action == 'close' and log_norm in open_start_by_norm:
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

    return {
        name: (sessions_by_name[name], totals_by_name[name])
        for name in requested
    }


def get_total_log_hours_for_file(
    file_path: str,
    now: Optional[datetime] = None,
    include_open_session: bool = False,
    log_paths: Optional[List[str]] = None,
) -> Tuple[float, int, List[str]]:
    """
    Sum historical hours for a file across all VW log files.
    Returns (total_hours, session_count, log_paths_used).

    By default excludes the current unclosed log session so live tracking
    does not double-count time while the file is open.
    """
    project_name = os.path.basename(file_path)
    total_hours = 0.0
    session_count = 0
    used_paths: List[str] = []

    for log_path in (log_paths or find_all_log_paths()):
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
    """Breakdown of log time vs VectorTrack live time."""
    closed_hours: float
    current_open_hours: float
    total_log_hours: float
    session_count: int
    log_paths: List[str]

    @property
    def historical_hours(self) -> float:
        """Completed sessions only — safe to add alongside VectorTrack live."""
        return self.closed_hours


def get_log_reconciliation(
    file_path: str,
    vt_live_hours: float = 0.0,
    now: Optional[datetime] = None,
    log_paths: Optional[List[str]] = None,
) -> LogReconciliation:
    """
    Parse all VW logs for a file and compute balance vs VectorTrack live time.
    balance_delta = log current open session hours - vt_live_hours
    """
    project_name = os.path.basename(file_path)
    closed_hours = 0.0
    current_open_hours = 0.0
    session_count = 0
    used_paths: List[str] = []

    for log_path in (log_paths or find_all_log_paths()):
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
    """Positive delta means Vectorworks log shows more current-session time than VectorTrack."""
    return round(reconciliation.current_open_hours - vt_live_hours, 2)
