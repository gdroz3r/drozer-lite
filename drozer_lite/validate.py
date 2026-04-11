"""Strict JSON schema validation for LLM output.

Parses the LLM response, tolerantly extracts a JSON object (the model
sometimes wraps output in a ```json fence even when told not to), and
validates it against `schemas/native.json`.

Returns the parsed dict or raises `SchemaValidationError` with enough
detail for the audit pipeline to log a warning and either retry or
surface the error.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "native.json"

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class SchemaValidationError(Exception):
    """Raised when the LLM response cannot be parsed or fails schema validation."""


@lru_cache(maxsize=1)
def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _extract_json_text(raw: str) -> str:
    """Pull the JSON object out of `raw`, tolerating markdown fences and prose.

    Strategy:
    1. If a ```json ... ``` (or plain ``` ... ```) fence exists, use the
       innermost contents.
    2. Otherwise, slice from the first '{' to the last '}'.
    3. Return the result; the caller will attempt json.loads and handle
       parse errors uniformly.
    """
    raw = raw.strip()
    if not raw:
        return raw

    fence = _FENCE_RE.search(raw)
    if fence:
        return fence.group(1).strip()

    first = raw.find("{")
    last = raw.rfind("}")
    if first != -1 and last != -1 and last > first:
        return raw[first : last + 1]

    return raw


def parse_and_validate(raw_response: str) -> dict[str, Any]:
    """Parse JSON from `raw_response` and validate against the native schema.

    Raises SchemaValidationError on parse failure or schema mismatch.
    """
    text = _extract_json_text(raw_response)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SchemaValidationError(f"response is not valid JSON: {exc.msg}") from exc

    if not isinstance(parsed, dict):
        raise SchemaValidationError(
            f"response root must be a JSON object, got {type(parsed).__name__}"
        )

    schema = _load_schema()
    try:
        jsonschema.validate(instance=parsed, schema=schema)
    except jsonschema.ValidationError as exc:
        path = "/".join(str(p) for p in exc.absolute_path) or "<root>"
        raise SchemaValidationError(f"schema violation at {path}: {exc.message}") from exc

    return parsed
