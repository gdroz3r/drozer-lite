"""Inline root-cause deduplication.

Cluster findings by (vulnerability_type, affected_function) and keep the
highest-severity representative per cluster. Ported from the main drozer
pipeline's `harnesses/dedup/root_cause_dedup.py`.

Populated in Build Phase 4.
"""

from __future__ import annotations


def dedup_findings(findings: list[dict]) -> list[dict]:
    """Collapse duplicate findings by root cause, keeping the highest severity."""
    raise NotImplementedError("Build Phase 4")
