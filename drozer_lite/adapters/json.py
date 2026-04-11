"""Native JSON output adapter — drozer-lite's own schema.

Matches `drozer_lite/schemas/native.json`. Preferred format for downstream
tooling, CI pipelines, and programmatic consumers.

Populated in Build Phase 4.
"""

from __future__ import annotations

from drozer_lite.audit import AuditResult


def format_json(result: AuditResult) -> str:
    raise NotImplementedError("Build Phase 4")
