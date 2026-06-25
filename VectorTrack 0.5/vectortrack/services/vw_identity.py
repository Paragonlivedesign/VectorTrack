"""Derive stable machine identity from Vectorworks install data."""

from __future__ import annotations

import hashlib
import json
import re
import socket
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from vectortrack.log_parser import (
    expected_log_path_for_year,
    find_all_log_paths,
    vectorworks_log_roaming_dir,
)

MACHINE_UUID_FILENAME = "machine_uuid.txt"
VW_USER_LOG_FILENAME = "VW User Log.txt"
LICENSE_ID_RE = re.compile(r"licenseID:\s*([A-Z0-9-]+)", re.IGNORECASE)

_identity_cache: dict[int | None, "VWIdentity"] = {}


@dataclass(frozen=True)
class VWIdentity:
    machine_uuid: str
    license_id: str
    license_suffix: str
    vw_session: str
    serial_masked: str
    hostname: str
    vw_year: int | None

    @property
    def machine_id(self) -> str:
        if self.machine_uuid:
            return self.machine_uuid.lower()
        return hostname_hash_machine_id()

    @property
    def default_label(self) -> str:
        suffix = self.license_suffix or self.license_id or "Vectorworks"
        return f"{self.hostname} ({suffix})"

    def to_mapping(self) -> dict[str, str]:
        return {
            "machine_uuid": self.machine_uuid,
            "license_id": self.license_id,
            "license_suffix": self.license_suffix,
            "hostname": self.hostname,
            "machine_id": self.machine_id,
            "default_label": self.default_label,
        }


def hostname_hash_machine_id() -> str:
    hostname = socket.gethostname() or "unknown"
    return hashlib.sha256(hostname.encode("utf-8")).hexdigest()[:16]


def is_legacy_hostname_machine_id(machine_id: str) -> bool:
    value = (machine_id or "").strip()
    return not value or value == hostname_hash_machine_id()


def vw_year_from_log_path(log_path: str) -> int | None:
    for part in log_path.replace("\\", "/").split("/"):
        if part.isdigit() and len(part) == 4:
            year = int(part)
            if 2000 <= year <= 2100:
                return year
    return None


def vw_data_dir(vw_year: int | None = None) -> Path:
    if vw_year is not None:
        return Path(expected_log_path_for_year(vw_year)).parent
    paths = find_all_log_paths()
    if paths:
        return Path(paths[0]).parent
    return Path(vectorworks_log_roaming_dir()) / str(datetime.now().year)


def clear_vw_identity_cache() -> None:
    _identity_cache.clear()


def resolve_vw_identity(vw_year: int | None = None, *, refresh: bool = False) -> VWIdentity:
    if refresh:
        _identity_cache.pop(vw_year, None)
    cached = _identity_cache.get(vw_year)
    if cached is not None:
        return cached
    identity = _load_identity(vw_year)
    _identity_cache[vw_year] = identity
    return identity


def local_machine_id(vw_year: int | None = None) -> str:
    return resolve_vw_identity(vw_year).machine_id


def resolve_sync_machine_id(stored: str, vw_year: int | None = None) -> str:
    if is_legacy_hostname_machine_id(stored):
        return local_machine_id(vw_year)
    return stored.strip() or local_machine_id(vw_year)


def resolve_sync_machine_label(stored: str, vw_year: int | None = None) -> str:
    label = (stored or "").strip()
    if label:
        return label
    return resolve_vw_identity(vw_year).default_label


def _load_identity(vw_year: int | None) -> VWIdentity:
    data_dir = vw_data_dir(vw_year)
    resolved_year = int(data_dir.name) if data_dir.name.isdigit() else vw_year
    machine_uuid = _read_machine_uuid(data_dir)
    user_log = _parse_user_log_tail(data_dir / VW_USER_LOG_FILENAME)
    license_id = user_log.get("license_id") or _license_id_from_ldf(data_dir)
    license_suffix = _license_suffix(license_id, user_log.get("serial_masked", ""))
    return VWIdentity(
        machine_uuid=machine_uuid,
        license_id=license_id,
        license_suffix=license_suffix,
        vw_session=user_log.get("session", ""),
        serial_masked=user_log.get("serial_masked", ""),
        hostname=socket.gethostname() or "unknown",
        vw_year=resolved_year,
    )


def _read_machine_uuid(data_dir: Path) -> str:
    path = data_dir / MACHINE_UUID_FILENAME
    if not path.is_file():
        return ""
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if re.fullmatch(r"[0-9a-fA-F-]{36}", value):
        return value.lower()
    return ""


def _license_id_from_ldf(data_dir: Path) -> str:
    if not data_dir.is_dir():
        return ""
    try:
        entries = sorted(data_dir.glob("*.ldf"))
    except OSError:
        return ""
    for entry in entries:
        stem = entry.stem.strip()
        if stem and "-" in stem:
            return stem
    return ""


def _license_suffix(license_id: str, serial_masked: str) -> str:
    if license_id and "-" in license_id:
        return license_id.rsplit("-", 1)[-1]
    if serial_masked and "-" in serial_masked:
        return serial_masked.rsplit("-", 1)[-1]
    return ""


def _parse_user_log_tail(path: Path, max_bytes: int = 512_000) -> dict[str, str]:
    result = {"serial_masked": "", "session": "", "license_id": ""}
    if not path.is_file():
        return result
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            handle.seek(max(0, size - max_bytes))
            chunk = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return result

    for line in reversed(chunk.splitlines()):
        parsed = _parse_user_log_line(line)
        if parsed is None:
            continue
        if not result["serial_masked"] and parsed.get("serial_masked"):
            result["serial_masked"] = parsed["serial_masked"]
        if not result["session"] and parsed.get("session"):
            result["session"] = parsed["session"]
        if not result["license_id"] and parsed.get("license_id"):
            result["license_id"] = parsed["license_id"]
        if all(result.values()):
            break
    return result


def _parse_user_log_line(line: str) -> dict[str, str] | None:
    text = line.strip()
    if not text.startswith("{"):
        return None
    try:
        payload: Any = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None

    parsed: dict[str, str] = {}
    serial = payload.get("sn")
    if isinstance(serial, str) and serial.strip():
        parsed["serial_masked"] = serial.strip()
    session = payload.get("session")
    if isinstance(session, str) and session.strip():
        parsed["session"] = session.strip()
    message = str(payload.get("message") or "")
    match = LICENSE_ID_RE.search(message)
    if match:
        parsed["license_id"] = match.group(1).upper()
    return parsed or None
