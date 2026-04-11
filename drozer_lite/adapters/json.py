"""JSON output adapter — drozer-lite native schema.

Serializes an AuditResult to its canonical JSON form, matching
`schemas/native.json`. Cluster metadata added by dedup is included as
optional fields on each finding so downstream consumers can filter to
representatives.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from drozer_lite.audit import AuditResult


def _finding_to_dict(f) -> dict:
    base = asdict(f)
    base = {k: v for k, v in base.items() if v is not None}
    for attr in ("cluster_id", "cluster_size", "is_cluster_representative"):
        if hasattr(f, attr):
            base[attr] = getattr(f, attr)
    return base


def format_json(result: AuditResult) -> str:
    payload = {
        "scanner": result.scanner,
        "version": result.version,
        "profiles_used": result.profiles_used,
        "files_analyzed": result.files_analyzed,
        "findings": [_finding_to_dict(f) for f in result.findings],
        "stats": result.stats,
        "warnings": result.warnings,
    }
    return json.dumps(payload, indent=2)
