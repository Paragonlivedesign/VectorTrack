"""
Vectorworks log discovery and session parsing (no vs dependency — unit-testable).
"""

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Set, Tuple

LOG_FILENAME = 'Vectorworks Log.txt'
YEAR_MIN = 2020
YEAR_MAX = 2030

# Native Vectorworks log: "11/24/2025  6:38:53 PM \t Opened \"file.vwx\"."
VW_EVENT_RE = re.compile(
    r'^(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2}\s+[AP]M)\s+'
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
TIMESTAMP_FMT = '%m/%d/%Y %I:%M:%S %p'


@dataclass
class SessionRecord:
    start: datetime
    end: datetime
    hours: float
    is_open: bool = False

    @property
    def duration_hours(self) -> float:
        return self.hours


def _normalize_project_name(name: str) -> str:
    return os.path.basename((name or '').replace('\\', '/')).strip().lower()


def _parse_timestamp(text: str) -> datetime:
    normalized = re.sub(r'\s+', ' ', text.strip())
    return datetime.strptime(normalized, TIMESTAMP_FMT)


def _parse_log_event(line: str) -> Optional[Tuple[str, datetime, str]]:
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
    stripped = line.strip()
    if not stripped:
        return None
    match = SAVE_AS_RE.search(stripped)
    if not match:
        return None
    return match.group(1), match.group(2)


def _roaming_root() -> str:
    return os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Nemetschek', 'Vectorworks')


def find_log_path(preferred_year: Optional[int] = None) -> Optional[str]:
    """
    Locate Vectorworks Log.txt.
    Tries preferred_year first, then scans YEAR_MIN..YEAR_MAX (newest first).
    """
    root = _roaming_root()
    if not os.path.isdir(root):
        return None

    years: List[int] = []
    if preferred_year is not None:
        years.append(preferred_year)
    for year in range(YEAR_MAX, YEAR_MIN - 1, -1):
        if year not in years:
            years.append(year)

    for year in years:
        candidate = os.path.join(root, str(year), LOG_FILENAME)
        if os.path.isfile(candidate):
            return candidate
    return None


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
    aliases: Optional[Sequence[str]] = None,
    now: Optional[datetime] = None,
) -> Tuple[List[SessionRecord], float]:
    """
    Parse open/close pairs for project_name from log content.
    Returns (sessions, total_hours).
    """
    alias_list = [project_name, *(aliases or [])]
    parsed = parse_sessions_for_aliases(content, alias_list, now=now)
    all_sessions: List[SessionRecord] = []
    seen = set()
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

    return {name: (sessions_by_name[name], totals_by_name[name]) for name in requested}


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
    client_name: str = '',
    budget_hours: Optional[float] = None,
    trust_note: str = '',
    max_sessions: int = 10,
) -> str:
    lines = [
        f'TIME TRACKING: {project_name}',
        '=' * 56,
        '',
    ]
    if client_name:
        lines.append(f'Client: {client_name}')
    if budget_hours is not None and budget_hours > 0:
        remaining = max(0.0, budget_hours - total_hours)
        lines.append(f'Budget: {budget_hours:.2f} hrs')
        lines.append(f'Budget Remaining: {remaining:.2f} hrs')
    if trust_note:
        lines.append(f'Log Trust: {trust_note}')
    lines.extend(['', 'SESSIONS:'])

    display = sessions[-max_sessions:] if len(sessions) > max_sessions else sessions
    offset = len(sessions) - len(display)
    for i, session in enumerate(display, start=offset + 1):
        lines.append(format_session_line(session, i, len(sessions)))

    if len(sessions) > max_sessions:
        lines.append(f'  ... and {len(sessions) - max_sessions} more sessions')

    total_amount = total_hours * rate
    lines.extend([
        '',
        '-' * 56,
        f'Total Hours: {total_hours:.2f}',
        f'Rate: ${rate:.2f}/hour',
        f'TOTAL AMOUNT: ${total_amount:.2f}',
        '-' * 56,
    ])
    return '\n'.join(lines)
