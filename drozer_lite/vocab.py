"""Vulnerability vocabulary — drozer-lite's native tag set.

Each native tag is a short, developer-readable name with optional SWC
Registry and CWE cross-references. Output adapters translate native tags
to benchmark-specific conventions (e.g., Forefy's `checks_effects_interactions_violation`).

drozer-lite uses natural tags in its native output so that the tool is
useful outside any single benchmark and so the README is readable.

Populated in Build Phase 4.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VocabEntry:
    tag: str
    description: str
    swc_id: str | None = None
    cwe_id: str | None = None


# Build Phase 4 will populate this with ~30 entries.
# Shape example:
# VOCABULARY = {
#     "reentrancy": VocabEntry(
#         tag="reentrancy",
#         description="External call before state update, re-entrant caller drains.",
#         swc_id="SWC-107",
#         cwe_id="CWE-841",
#     ),
#     ...
# }
VOCABULARY: dict[str, VocabEntry] = {}


def canonicalize(raw_type: str) -> str:
    """Map a free-form vulnerability type string to a canonical native tag.

    If no match is found, the original string is returned unchanged and
    flagged upstream as `canonical_mapping: "unmapped"`.
    """
    raise NotImplementedError("Build Phase 4")
