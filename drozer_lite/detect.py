"""Deterministic protocol type detection.

Given a set of source files, score each profile against the concatenated
source using regex patterns loaded from `profiles.json`. Return the
selection: always-loaded profiles + any auto-detected profiles whose score
clears the configured threshold.

No LLM is involved. Detection is pure and reproducible.

Profiles listed under `explicit_only` in profiles.json are NEVER auto-
selected, regardless of score. They must be passed via `--profile`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

ProfileName = str

PROFILES_JSON = Path(__file__).resolve().parent.parent / "profiles.json"


@dataclass
class ProfileSelection:
    selected: list[ProfileName]
    scores: dict[ProfileName, int] = field(default_factory=dict)
    source: str = "auto"  # "auto" or "user-override"


@lru_cache(maxsize=1)
def _load_profiles_config() -> dict:
    if not PROFILES_JSON.is_file():
        raise FileNotFoundError(f"profiles.json not found at {PROFILES_JSON}")
    return json.loads(PROFILES_JSON.read_text(encoding="utf-8"))


def _compile_patterns(config: dict) -> dict[ProfileName, list[re.Pattern[str]]]:
    compiled: dict[ProfileName, list[re.Pattern[str]]] = {}
    for name, body in config.get("profiles", {}).items():
        compiled[name] = [re.compile(p) for p in body.get("patterns", [])]
    return compiled


def detect_profiles(files: list[tuple[str, str]]) -> ProfileSelection:
    """Score every profile against the source and return the selection.

    Always includes profiles listed under `always_loaded` in profiles.json
    (typically `universal`). Auto-includes profiles whose match count
    clears the configured threshold. Profiles in `explicit_only` are
    skipped — they must be requested by name.
    """
    config = _load_profiles_config()
    threshold: int = int(config.get("threshold", 3))
    always_loaded: list[str] = list(config.get("always_loaded", []))
    explicit_only = set(config.get("explicit_only", []))

    compiled = _compile_patterns(config)
    blob = "\n".join(content for _, content in files)

    scores: dict[ProfileName, int] = {}
    for name, patterns in compiled.items():
        if name in explicit_only or not patterns:
            continue
        scores[name] = sum(1 for p in patterns if p.search(blob))

    selected: list[ProfileName] = list(always_loaded)
    for name, score in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])):
        if score >= threshold and name not in selected:
            selected.append(name)

    return ProfileSelection(selected=selected, scores=scores, source="auto")


def select_profiles(
    files: list[tuple[str, str]],
    *,
    override: str | None = None,
) -> ProfileSelection:
    """Top-level profile selection used by the audit pipeline.

    If `override` is None or 'auto', delegate to `detect_profiles`.
    Otherwise return a user-override selection: always-loaded + the
    requested profile (which may be an explicit-only profile like icp/
    solana).
    """
    if override is None or override == "auto":
        return detect_profiles(files)

    config = _load_profiles_config()
    always_loaded: list[str] = list(config.get("always_loaded", []))
    selected = list(always_loaded)
    if override not in selected:
        selected.append(override)
    return ProfileSelection(selected=selected, scores={}, source="user-override")
