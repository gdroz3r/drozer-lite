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

# Populated as adapters are implemented in Build Phase 4.
_REGISTRY: dict[str, AdapterFn] = {}


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
