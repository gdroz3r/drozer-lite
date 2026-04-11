"""Tests for validate.py — JSON parse + schema validation."""

from __future__ import annotations

import json

import pytest

from drozer_lite.validate import SchemaValidationError, parse_and_validate

VALID_PAYLOAD = {
    "scanner": "drozer-lite",
    "version": "0.1.0",
    "profiles_used": ["universal"],
    "files_analyzed": ["A.sol"],
    "findings": [
        {
            "vulnerability_type": "reentrancy",
            "affected_function": "withdraw",
            "affected_file": "A.sol",
            "severity": "HIGH",
            "explanation": "External call before state update.",
            "line_hint": 12,
            "confidence": "HIGH",
            "source_profile": "reentrancy",
        }
    ],
}


def test_parse_valid_payload() -> None:
    out = parse_and_validate(json.dumps(VALID_PAYLOAD))
    assert out["scanner"] == "drozer-lite"
    assert len(out["findings"]) == 1


def test_parse_payload_in_json_fence() -> None:
    raw = "```json\n" + json.dumps(VALID_PAYLOAD) + "\n```"
    out = parse_and_validate(raw)
    assert out["scanner"] == "drozer-lite"


def test_parse_payload_in_plain_fence() -> None:
    raw = "```\n" + json.dumps(VALID_PAYLOAD) + "\n```"
    out = parse_and_validate(raw)
    assert out["scanner"] == "drozer-lite"


def test_parse_payload_with_prose_prefix() -> None:
    raw = "Here is the result:\n" + json.dumps(VALID_PAYLOAD) + "\nDone."
    out = parse_and_validate(raw)
    assert out["scanner"] == "drozer-lite"


def test_invalid_json_raises() -> None:
    with pytest.raises(SchemaValidationError, match="not valid JSON"):
        parse_and_validate("not json at all")


def test_root_must_be_object() -> None:
    with pytest.raises(SchemaValidationError, match="must be a JSON object"):
        parse_and_validate("[]")


def test_missing_required_field_raises() -> None:
    payload = {"scanner": "drozer-lite", "version": "0.1.0"}  # missing findings
    with pytest.raises(SchemaValidationError, match="schema violation"):
        parse_and_validate(json.dumps(payload))


def test_wrong_severity_enum_raises() -> None:
    bad = json.loads(json.dumps(VALID_PAYLOAD))
    bad["findings"][0]["severity"] = "EXTREME"
    with pytest.raises(SchemaValidationError, match="schema violation"):
        parse_and_validate(json.dumps(bad))


def test_empty_findings_array_is_valid() -> None:
    payload = {"scanner": "drozer-lite", "version": "0.1.0", "findings": []}
    out = parse_and_validate(json.dumps(payload))
    assert out["findings"] == []


def test_wrong_scanner_name_raises() -> None:
    bad = json.loads(json.dumps(VALID_PAYLOAD))
    bad["scanner"] = "not-drozer-lite"
    with pytest.raises(SchemaValidationError, match="schema violation"):
        parse_and_validate(json.dumps(bad))
