"""Core audit API — library-callable entry points.

This module exposes two functions that are the canonical way to invoke
drozer-lite from Python code. The CLI is a thin wrapper over these.

    audit_path(path: str | Path, **options) -> AuditResult
    audit_source(files: list[tuple[str, str]], **options) -> AuditResult

The rest of the package (detect, checklist, prompt, llm, validate, vocab,
dedup, adapters) are implementation details. Downstream consumers should
only import from this module or the top-level `drozer_lite` package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Finding:
    """A single vulnerability finding.

    Uses drozer-lite's native vocabulary. Optional SWC/CWE cross-references
    are populated when the vocabulary map has them. Adapters can translate
    this to benchmark-specific formats.
    """

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
    original_type: str | None = None  # the LLM's raw output before vocab mapping


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


def audit_path(
    path: str | Path,
    *,
    profile: str | None = None,
    model: str = "claude-opus-4-6",
    max_bytes: int = 20_000,
) -> AuditResult:
    """Audit a .sol file or a directory of .sol files.

    Parameters
    ----------
    path
        Path to a .sol file or a directory containing .sol files.
        Directories are walked recursively, excluding node_modules, lib,
        test, and mock directories.
    profile
        Optional override. If None, drozer-lite detects the protocol type
        from the source using deterministic regex patterns.
    model
        Anthropic model identifier. Defaults to claude-opus-4-6.
    max_bytes
        Safety ceiling on total source size. Files exceeding this are
        refused with a warning. The full drozer pipeline should be used
        for larger codebases.

    Returns
    -------
    AuditResult
        Structured result with findings, profiles used, stats.
    """
    raise NotImplementedError("Build Phase 1 scaffold — implementation lands in Build Phase 3")


def audit_source(
    files: list[tuple[str, str]],
    *,
    profile: str | None = None,
    model: str = "claude-opus-4-6",
) -> AuditResult:
    """Audit in-memory contract source(s).

    Parameters
    ----------
    files
        List of (filename, content) tuples. Useful for stdin or tests.
    profile
        Optional override. See `audit_path`.
    model
        Anthropic model identifier.

    Returns
    -------
    AuditResult
    """
    raise NotImplementedError("Build Phase 1 scaffold — implementation lands in Build Phase 3")
