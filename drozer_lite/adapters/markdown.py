"""Markdown output adapter — the DEFAULT for drozer-lite CLI users.

Formats an AuditResult as a human-readable report with a summary,
per-finding sections grouped by severity, and optional metadata footer.

Populated in Build Phase 4.
"""

from __future__ import annotations

from drozer_lite.audit import AuditResult


def format_markdown(result: AuditResult) -> str:
    raise NotImplementedError("Build Phase 4")
