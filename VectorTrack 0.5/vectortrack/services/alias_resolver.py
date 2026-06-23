"""Alias matching for project/file name resolution."""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class AliasMatch:
    """Match details returned by :class:`AliasResolver`."""

    canonical: str
    alias: str
    strategy: str
    confidence: float


class AliasResolver:
    """
    Resolve project names to canonical IDs using layered matching:
    exact -> prefix -> pattern -> version heuristic.
    """

    _VERSION_TOKEN_RE = re.compile(r"[\s._-]*(?:v|ver|rev)?\d{1,4}[a-z]?$", re.IGNORECASE)

    def __init__(self, aliases: Optional[Dict[str, Iterable[str]]] = None):
        self._aliases_by_canonical: Dict[str, List[str]] = {}
        self._exact_index: Dict[str, str] = {}
        if aliases:
            for canonical, values in aliases.items():
                self.register(canonical, values)

    @staticmethod
    def normalize_name(value: str) -> str:
        if not value:
            return ""
        basename = os.path.basename(value.replace("\\", "/")).strip()
        return basename.lower()

    @classmethod
    def _strip_version_suffix(cls, value: str) -> str:
        stem, _ext = os.path.splitext(value)
        cleaned = cls._VERSION_TOKEN_RE.sub("", stem)
        cleaned = re.sub(r"[\s._-]+$", "", cleaned)
        return cleaned

    def register(self, canonical: str, aliases: Iterable[str]) -> None:
        canonical_norm = self.normalize_name(canonical)
        merged = [canonical]
        merged.extend(alias for alias in aliases if alias)
        existing = self._aliases_by_canonical.get(canonical_norm, [])
        for candidate in merged:
            norm = self.normalize_name(candidate)
            if not norm:
                continue
            if candidate not in existing:
                existing.append(candidate)
            self._exact_index[norm] = canonical
        self._aliases_by_canonical[canonical_norm] = existing

    def resolve(self, value: str) -> Optional[AliasMatch]:
        if not value:
            return None
        normalized = self.normalize_name(value)
        if not normalized:
            return None

        exact = self._resolve_exact(normalized)
        if exact:
            return exact
        prefix = self._resolve_prefix(normalized)
        if prefix:
            return prefix
        pattern = self._resolve_pattern(normalized)
        if pattern:
            return pattern
        return self._resolve_version_heuristic(normalized)

    def resolve_name(self, value: str, default: Optional[str] = None) -> Optional[str]:
        match = self.resolve(value)
        return match.canonical if match else default

    def _resolve_exact(self, normalized: str) -> Optional[AliasMatch]:
        canonical = self._exact_index.get(normalized)
        if not canonical:
            return None
        return AliasMatch(
            canonical=canonical,
            alias=normalized,
            strategy="exact",
            confidence=1.0,
        )

    def _resolve_prefix(self, normalized: str) -> Optional[AliasMatch]:
        best: Optional[AliasMatch] = None
        for canonical_norm, aliases in self._aliases_by_canonical.items():
            canonical = self._exact_index.get(canonical_norm, aliases[0])
            for alias in aliases:
                alias_norm = self.normalize_name(alias)
                if not alias_norm or alias_norm == normalized:
                    continue
                # Leave pure version-token differences to version heuristic.
                if self._strip_version_suffix(alias_norm) == self._strip_version_suffix(normalized):
                    continue
                if normalized.startswith(alias_norm) or alias_norm.startswith(normalized):
                    candidate = AliasMatch(
                        canonical=canonical,
                        alias=alias,
                        strategy="prefix",
                        confidence=0.9,
                    )
                    if best is None or len(alias_norm) > len(self.normalize_name(best.alias)):
                        best = candidate
        return best

    def _resolve_pattern(self, normalized: str) -> Optional[AliasMatch]:
        for canonical_norm, aliases in self._aliases_by_canonical.items():
            canonical = self._exact_index.get(canonical_norm, aliases[0])
            for alias in aliases:
                if "*" not in alias and "?" not in alias:
                    continue
                if fnmatch.fnmatch(normalized, self.normalize_name(alias)):
                    return AliasMatch(
                        canonical=canonical,
                        alias=alias,
                        strategy="pattern",
                        confidence=0.82,
                    )
        return None

    def _resolve_version_heuristic(self, normalized: str) -> Optional[AliasMatch]:
        target_stem = self._strip_version_suffix(normalized)
        if not target_stem:
            return None
        for canonical_norm, aliases in self._aliases_by_canonical.items():
            canonical = self._exact_index.get(canonical_norm, aliases[0])
            for alias in aliases:
                alias_norm = self.normalize_name(alias)
                alias_stem = self._strip_version_suffix(alias_norm)
                if alias_stem and alias_stem == target_stem:
                    return AliasMatch(
                        canonical=canonical,
                        alias=alias,
                        strategy="version_heuristic",
                        confidence=0.75,
                    )
        return None
