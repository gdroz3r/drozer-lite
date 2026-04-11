"""Markdown output adapter — the DEFAULT for drozer-lite CLI users.

Formats an AuditResult as a human-readable report with a summary,
per-finding sections grouped by severity, and a metadata footer.
"""

from __future__ import annotations

from drozer_lite.audit import AuditResult, Finding

_SEV_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


def _summary_table(findings: list[Finding]) -> str:
    counts = dict.fromkeys(_SEV_ORDER, 0)
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    rows = "\n".join(f"| {sev:<8} | {counts[sev]:>5} |" for sev in _SEV_ORDER)
    return "| Severity | Count |\n|----------|-------|\n" + rows


def _format_finding(f: Finding, idx: int) -> str:
    line = f":L{f.line_hint}" if f.line_hint else ""
    swc = f" · {f.swc_id}" if f.swc_id else ""
    cwe = f" · {f.cwe_id}" if f.cwe_id else ""
    return (
        f"### {idx}. `{f.vulnerability_type}` — {f.severity}\n"
        f"**Function**: `{f.affected_function}`  \n"
        f"**File**: `{f.affected_file}{line}`  \n"
        f"**Profile**: `{f.source_profile}` · **Confidence**: {f.confidence}{swc}{cwe}\n\n"
        f"{f.explanation}\n"
    )


def format_markdown(result: AuditResult) -> str:
    lines: list[str] = []
    lines.append(f"# {result.scanner} report (v{result.version})\n")

    if result.profiles_used:
        lines.append(f"**Profiles**: {', '.join(result.profiles_used)}  ")
    if result.files_analyzed:
        lines.append(f"**Files analyzed** ({len(result.files_analyzed)}): "
                     f"{', '.join(result.files_analyzed)}\n")

    lines.append("## Summary\n")
    lines.append(_summary_table(result.findings) + "\n")

    if not result.findings:
        lines.append("\n_No findings._\n")
    else:
        sorted_findings = sorted(
            result.findings,
            key=lambda f: (_SEV_ORDER.index(f.severity) if f.severity in _SEV_ORDER else 99),
        )
        lines.append("\n## Findings\n")
        for idx, f in enumerate(sorted_findings, start=1):
            lines.append(_format_finding(f, idx))

    if result.warnings:
        lines.append("\n## Warnings\n")
        for w in result.warnings:
            lines.append(f"- {w}")
        lines.append("")

    if result.stats:
        lines.append("\n## Stats\n")
        for k, v in result.stats.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    return "\n".join(lines)
