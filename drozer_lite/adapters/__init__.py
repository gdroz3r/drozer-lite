"""Output format adapters.

Each adapter takes an `AuditResult` and returns a string (or writes a file)
in a specific output format. Adapters are registered via a simple dispatch
table so new ones can be contributed without touching core code.

Available adapters (Build Phase 4):
    markdown  - default human-readable report
    json      - native JSON schema
    sarif     - SARIF v2.1 for GitHub code scanning
    forefy    - Forefy autonomous-audit benchmark format
"""

from __future__ import annotations

from typing import Callable

from drozer_lite.audit import AuditResult

AdapterFn = Callable[[AuditResult], str]

_REGISTRY: dict[str, AdapterFn] = {}


def _bootstrap_default_adapters() -> None:
    """Register the markdown adapter (Phase 3). Other adapters land in Phase 4."""
    from drozer_lite.adapters.markdown import format_markdown

    _REGISTRY["markdown"] = format_markdown


_bootstrap_default_adapters()


def register(name: str, fn: AdapterFn) -> None:
    _REGISTRY[name] = fn


def emit(result: AuditResult, format: str) -> str:
    if format not in _REGISTRY:
        raise ValueError(
            f"Unknown output format: {format!r}. Available: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[format](result)


def available_formats() -> list[str]:
    return sorted(_REGISTRY.keys())
