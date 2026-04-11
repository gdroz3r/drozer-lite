"""SARIF v2.1 output adapter for CI integration.

SARIF (Static Analysis Results Interchange Format) is the format GitHub
code scanning, Azure DevOps, and several other CI systems ingest. Emitting
SARIF lets drozer-lite results show up inline in pull requests.

Reference: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html

Populated in Build Phase 4.
"""

from __future__ import annotations

from drozer_lite.audit import AuditResult


def format_sarif(result: AuditResult) -> str:
    raise NotImplementedError("Build Phase 4")
