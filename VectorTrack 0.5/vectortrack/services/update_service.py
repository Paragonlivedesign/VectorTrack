"""Check GitHub Releases for newer VectorTrack builds."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from vectortrack.config import APP_VERSION, GITHUB_RELEASES_LATEST_API, GITHUB_RELEASES_LATEST_URL

_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


@dataclass(frozen=True)
class ReleaseInfo:
    version: tuple[int, int, int]
    version_label: str
    release_url: str
    download_url: str | None
    notes: str


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: tuple[int, int, int]
    latest: ReleaseInfo | None
    error: str | None = None

    @property
    def update_available(self) -> bool:
        if self.latest is None or self.error:
            return False
        return self.latest.version > self.current_version


def parse_version(label: str) -> tuple[int, int, int] | None:
    match = _VERSION_RE.search(label or "")
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def current_version_tuple() -> tuple[int, int, int]:
    parsed = parse_version(APP_VERSION)
    if parsed is None:
        return (0, 0, 0)
    return parsed


def format_version_tuple(version: tuple[int, int, int]) -> str:
    return f"{version[0]}.{version[1]}.{version[2]}"


def _installer_download_url(assets: list[dict[str, Any]]) -> str | None:
    for asset in assets:
        name = str(asset.get("name", ""))
        if name.endswith("-Setup.exe") or name.endswith("Setup.exe"):
            url = asset.get("browser_download_url")
            if url:
                return str(url)
    return None


def release_info_from_payload(payload: dict[str, Any]) -> ReleaseInfo | None:
    tag_name = str(payload.get("tag_name", ""))
    version = parse_version(tag_name)
    if version is None:
        return None
    release_url = str(payload.get("html_url") or GITHUB_RELEASES_LATEST_URL)
    assets = payload.get("assets") or []
    download_url = _installer_download_url(assets) if isinstance(assets, list) else None
    notes = str(payload.get("body") or "").strip()
    return ReleaseInfo(
        version=version,
        version_label=tag_name.lstrip("vV"),
        release_url=release_url,
        download_url=download_url,
        notes=notes,
    )


def fetch_latest_release(api_url: str = GITHUB_RELEASES_LATEST_API) -> ReleaseInfo:
    request = urllib.request.Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"VectorTrack/{APP_VERSION}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError("No published releases were found on GitHub.") from exc
        raise RuntimeError(f"GitHub returned HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Could not reach GitHub. Check your internet connection.") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected response from GitHub.")
    release = release_info_from_payload(payload)
    if release is None:
        raise RuntimeError("Latest release tag is missing a version number.")
    return release


def check_for_updates() -> UpdateCheckResult:
    current = current_version_tuple()
    try:
        latest = fetch_latest_release()
    except Exception as exc:
        return UpdateCheckResult(current_version=current, latest=None, error=str(exc))
    return UpdateCheckResult(current_version=current, latest=latest)
