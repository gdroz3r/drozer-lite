"""Forefy benchmark output adapter.

> **Schema status**: provisional. The exact Forefy autonomous-audit benchmark
> JSON schema has not been validated against a real submission yet — that
> validation lands in Build Phase 6 (benchmark validation). The current
> implementation emits a flat list of findings using snake_case
> vulnerability_type values from drozer-lite's native vocabulary, plus the
> minimal fields described in public Forefy benchmark examples.
>
> If Phase 6 reveals schema differences, fix this adapter and add a
> regression test against a captured Forefy fixture.
"""

from __future__ import annotations

import json

from drozer_lite.audit import AuditResult, Finding
from drozer_lite.vocab import canonicalize


def _to_forefy(f: Finding) -> dict:
    canonical, _ = canonicalize(f.vulnerability_type)
    out: dict = {
        "vulnerability_type": canonical or f.vulnerability_type,
        "affected_function": f.affected_function,
        "affected_file": f.affected_file,
        "severity": (f.severity or "").lower(),
        "explanation": f.explanation,
    }
    if f.line_hint is not None:
        out["line"] = f.line_hint
    return out


def _representatives_only(findings: list[Finding]) -> list[Finding]:
    """Return only cluster representatives. Findings without cluster tags
    are treated as their own representative."""
    out: list[Finding] = []
    for f in findings:
        if not hasattr(f, "is_cluster_representative") or getattr(
            f, "is_cluster_representative"
        ):
            out.append(f)
    return out


def format_forefy(result: AuditResult) -> str:
    payload = {
        "scanner": result.scanner,
        "version": result.version,
        "findings": [_to_forefy(f) for f in _representatives_only(result.findings)],
    }
    return json.dumps(payload, indent=2)
