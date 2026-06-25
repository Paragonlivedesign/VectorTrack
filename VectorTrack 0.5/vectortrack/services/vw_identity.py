"""Derive stable machine identity from Vectorworks install data."""

from __future__ import annotations

import socket

from vectortrack_core.identity.machine import (  # noqa: F401
    LICENSE_ID_RE,
    MACHINE_UUID_FILENAME,
    VW_USER_LOG_FILENAME,
    VWIdentity,
    clear_vw_identity_cache,
    hostname_hash_machine_id,
    is_legacy_hostname_machine_id,
    local_machine_id,
    resolve_sync_machine_id,
    resolve_sync_machine_label,
    vw_year_from_log_path,
)
from vectortrack_core.identity import machine as _core


def vw_data_dir(vw_year: int | None = None):
    """Resolve Vectorworks data directory (patchable in tests)."""
    return _core.vw_data_dir(vw_year)


def resolve_vw_identity(vw_year: int | None = None, *, refresh: bool = False) -> VWIdentity:
    if refresh:
        _core._identity_cache.pop(vw_year, None)
    cached = _core._identity_cache.get(vw_year)
    if cached is not None:
        return cached
    identity = _load_identity(vw_year)
    _core._identity_cache[vw_year] = identity
    return identity


def _load_identity(vw_year: int | None) -> VWIdentity:
    data_dir = vw_data_dir(vw_year)
    resolved_year = int(data_dir.name) if data_dir.name.isdigit() else vw_year
    machine_uuid = _core._read_machine_uuid(data_dir)
    user_log = _core._parse_user_log_tail(data_dir / VW_USER_LOG_FILENAME)
    license_id = user_log.get("license_id") or _core._license_id_from_ldf(data_dir)
    license_suffix = _core._license_suffix(license_id, user_log.get("serial_masked", ""))
    return VWIdentity(
        machine_uuid=machine_uuid,
        license_id=license_id,
        license_suffix=license_suffix,
        vw_session=user_log.get("session", ""),
        serial_masked=user_log.get("serial_masked", ""),
        hostname=socket.gethostname() or "unknown",
        vw_year=resolved_year,
    )
