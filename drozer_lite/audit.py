"""Core audit API — library-callable entry points.

This module exposes two functions that are the canonical way to invoke
drozer-lite from Python code. The CLI is a thin wrapper over these.

    audit_path(path: str | Path, **options) -> AuditResult
    audit_source(files: list[tuple[str, str]], **options) -> AuditResult
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from drozer_lite import checklist, detect, llm, prompt, validate, vocab

EXCLUDED_DIR_NAMES = frozenset(
    {
        "node_modules",
        "lib",
        "test",
        "tests",
        "mock",
        "mocks",
        "script",
        "scripts",
        "out",
        "cache",
        ".git",
        ".forge",
        "broadcast",
    }
)


@dataclass
class Finding:
    """A single vulnerability finding (drozer-lite native shape)."""

    vulnerability_type: str
    affected_function: str
    affected_file: str
    severity: str
    explanation: str
    line_hint: int | None = None
    confidence: str = "MEDIUM"
    source_profile: str = "universal"
    swc_id: str | None = None
    cwe_id: str | None = None
    original_type: str | None = None


@dataclass
class AuditResult:
    """Result of a single drozer-lite invocation."""

    scanner: str = "drozer-lite"
    version: str = "0.1.0"
    profiles_used: list[str] = field(default_factory=list)
    files_analyzed: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _collect_sol_files(path: Path, max_bytes: int) -> tuple[list[tuple[str, str]], list[str]]:
    """Walk `path` and return (files, warnings).

    Skips standard non-source directories. Refuses if total size exceeds
    `max_bytes` — the caller should fall back to the full drozer pipeline
    for larger codebases.
    """
    warnings: list[str] = []

    if path.is_file():
        if path.suffix != ".sol":
            warnings.append(f"file is not a .sol file: {path}")
            return [], warnings
        content = path.read_text(encoding="utf-8", errors="replace")
        size = len(content.encode("utf-8"))
        if size > max_bytes:
            warnings.append(
                f"file exceeds max_bytes ({size} > {max_bytes}); use the full drozer pipeline"
            )
            return [], warnings
        return [(path.name, content)], warnings

    if not path.is_dir():
        warnings.append(f"path does not exist: {path}")
        return [], warnings

    collected: list[tuple[str, str]] = []
    total = 0
    for sol in sorted(path.rglob("*.sol")):
        if any(part in EXCLUDED_DIR_NAMES for part in sol.parts):
            continue
        try:
            content = sol.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            warnings.append(f"could not read {sol}: {exc}")
            continue
        size = len(content.encode("utf-8"))
        if total + size > max_bytes:
            warnings.append(
                f"max_bytes ({max_bytes}) reached; skipped remaining files starting at {sol}. "
                f"use the full drozer pipeline for larger codebases."
            )
            break
        rel = sol.relative_to(path).as_posix()
        collected.append((rel, content))
        total += size

    return collected, warnings


def _to_finding(raw: dict[str, Any]) -> Finding:
    raw_type = raw["vulnerability_type"]
    canonical, was_mapped = vocab.canonicalize(raw_type)
    entry = vocab.lookup(canonical) if was_mapped else None
    return Finding(
        vulnerability_type=canonical if was_mapped else raw_type,
        affected_function=raw["affected_function"],
        affected_file=raw["affected_file"],
        severity=raw["severity"],
        explanation=raw["explanation"],
        line_hint=raw.get("line_hint"),
        confidence=raw.get("confidence", "MEDIUM"),
        source_profile=raw.get("source_profile", "universal"),
        swc_id=raw.get("swc_id") or (entry.swc_id if entry else None),
        cwe_id=raw.get("cwe_id") or (entry.cwe_id if entry else None),
        original_type=raw_type if was_mapped and canonical != raw_type else raw.get("original_type"),
    )


def audit_source(
    files: list[tuple[str, str]],
    *,
    profile: str | None = None,
    model: str = llm.DEFAULT_MODEL,
) -> AuditResult:
    """Audit in-memory contract source(s).

    Parameters
    ----------
    files
        List of (filename, content) tuples. Useful for stdin or tests.
    profile
        Optional override. None or "auto" → deterministic regex detection.
        Otherwise the named profile is loaded alongside `universal`.
    model
        Anthropic model identifier.
    """
    result = AuditResult()

    if not files:
        result.warnings.append("no source files provided")
        return result

    selection = detect.select_profiles(files, override=profile)
    result.profiles_used = list(selection.selected)
    result.files_analyzed = [name for name, _ in files]

    try:
        loaded_checklist = checklist.load_checklist(selection.selected)
    except checklist.ChecklistNotFoundError as exc:
        result.warnings.append(f"checklist load failed: {exc}")
        return result

    built = prompt.build_prompt(
        loaded_checklist,
        files,
        profiles_used=selection.selected,
    )

    started = time.monotonic()
    try:
        response = llm.call_llm(system=built.system, user=built.user, model=model)
    except llm.LLMError as exc:
        result.warnings.append(f"LLM call failed: {exc}")
        return result
    wall = time.monotonic() - started

    try:
        parsed = validate.parse_and_validate(response.text)
    except validate.SchemaValidationError as exc:
        result.warnings.append(f"schema validation failed: {exc}")
        return result

    raw_findings = [_to_finding(f) for f in parsed.get("findings", [])]

    # Inline dedup — tags findings with cluster metadata, sorts representatives first.
    from drozer_lite import dedup  # local import to avoid circular dep at import time

    deduped, dedup_stats = dedup.dedup_findings(raw_findings)
    result.findings = deduped
    result.stats = {
        "llm_calls": 1,
        "wall_time_sec": round(wall, 2),
        "retries": response.retries,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "cached_tokens": response.cached_tokens,
        "model": response.model,
        "dedup_total": dedup_stats.total_findings,
        "dedup_representatives": dedup_stats.representatives,
        "dedup_merged_away": dedup_stats.merged_away,
    }
    return result


def audit_path(
    path: str | Path,
    *,
    profile: str | None = None,
    model: str = llm.DEFAULT_MODEL,
    max_bytes: int = 20_000,
) -> AuditResult:
    """Audit a .sol file or a directory of .sol files."""
    p = Path(path)
    files, warnings = _collect_sol_files(p, max_bytes)

    if not files:
        result = AuditResult()
        result.warnings = warnings
        return result

    result = audit_source(files, profile=profile, model=model)
    result.warnings = warnings + result.warnings
    return result
