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
    """Register the four built-in adapters."""
    from drozer_lite.adapters.forefy import format_forefy
    from drozer_lite.adapters.json import format_json
    from drozer_lite.adapters.markdown import format_markdown
    from drozer_lite.adapters.sarif import format_sarif

    _REGISTRY["markdown"] = format_markdown
    _REGISTRY["json"] = format_json
    _REGISTRY["sarif"] = format_sarif
    _REGISTRY["forefy"] = format_forefy


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
