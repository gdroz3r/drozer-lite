"""Deterministic protocol type detection.

Given a set of .sol files, score each profile against the concatenated source
using regex patterns loaded from `profiles.json`. Return the top matching
profile names (always including `universal`).

No LLM is involved. Detection must be pure and reproducible.

Populated in Build Phase 2.
"""

from __future__ import annotations

from dataclasses import dataclass

ProfileName = str


@dataclass
class ProfileSelection:
    selected: list[ProfileName]
    scores: dict[ProfileName, int]
    source: str  # "auto" or "user-override"


def detect_profiles(files: list[tuple[str, str]]) -> ProfileSelection:
    """Score every profile against the source and return the top matches.

    Always includes `universal` in the selection. Additional profiles are
    included only if their score clears a threshold (defined in Build Phase 2).
    """
    raise NotImplementedError("Build Phase 2")
