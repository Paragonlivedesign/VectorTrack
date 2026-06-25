"""Shared sync I/O helpers."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path


def atomic_write_text(path: str, content: str) -> None:
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        handle.write(content)
    os.replace(temp_path, path)


def atomic_write_json(path: str, payload: dict) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2))


def read_json_file(path: str) -> dict:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return {}


def parse_updated_at(raw: object) -> datetime:
    if not raw:
        return datetime.min
    try:
        return datetime.fromisoformat(str(raw))
    except (TypeError, ValueError):
        return datetime.min
