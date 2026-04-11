"""Strict JSON schema validation for LLM output.

Parses the LLM response, validates it against `schemas/native.json`, and
returns a typed `AuditResult` or raises a specific validation error that
the audit pipeline can choose to retry or surface.

Populated in Build Phase 3.
"""

from __future__ import annotations


class SchemaValidationError(Exception):
    """Raised when the LLM response does not match the expected schema."""


def parse_and_validate(raw_response: str) -> dict:
    """Parse JSON from `raw_response` and validate against the native schema."""
    raise NotImplementedError("Build Phase 3")
