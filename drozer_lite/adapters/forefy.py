"""Forefy autonomous-audit benchmark format adapter.

Translates drozer-lite's native output to the schema expected by
https://forefy.com/benchmarks — one of several benchmark adapters. Not
privileged over the others; used only when `--format forefy` is requested.

The translation step applies a vocabulary map from drozer-lite's native
tags (e.g., `reentrancy`) to Forefy's exact normalized tags (e.g.,
`checks_effects_interactions_violation`).

Populated in Build Phase 4.
"""

from __future__ import annotations

from drozer_lite.audit import AuditResult


def format_forefy(result: AuditResult) -> str:
    raise NotImplementedError("Build Phase 4")
