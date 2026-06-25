"""
Parse Vectorworks Log.txt for historical file open/close sessions.

Re-exports from vectortrack_core for backward compatibility.
"""

from vectortrack_core.log import parser as _core
from vectortrack_core.log.parser import *  # noqa: F403

# Private helpers referenced by tests and legacy callers
_roaming_root = _core._roaming_root
_normalize_project_name = _core.normalize_project_name
_parse_log_event = _core._parse_log_event
_parse_save_as_alias = _core._parse_save_as_alias
_parse_timestamp = _core._parse_timestamp
_names_match = _core._names_match
