"""Tests for the four output adapters."""

from __future__ import annotations

import json

import pytest

from drozer_lite.adapters import available_formats, emit
from drozer_lite.adapters.forefy import format_forefy
from drozer_lite.adapters.json import format_json
from drozer_lite.adapters.markdown import format_markdown
from drozer_lite.adapters.sarif import format_sarif
from drozer_lite.audit import AuditResult, Finding


def _result_with_findings() -> AuditResult:
    return AuditResult(
        profiles_used=["universal", "vault"],
        files_analyzed=["Vault.sol"],
        findings=[
            Finding(
                vulnerability_type="reentrancy",
                affected_function="withdraw",
                affected_file="Vault.sol",
                severity="HIGH",
                explanation="External call before state update.",
                line_hint=12,
                confidence="HIGH",
                source_profile="reentrancy",
                swc_id="SWC-107",
                cwe_id="CWE-841",
            ),
            Finding(
                vulnerability_type="missing_access_control",
                affected_function="setOwner",
                affected_file="Vault.sol",
                severity="CRITICAL",
                explanation="setOwner has no access control.",
                line_hint=5,
                confidence="HIGH",
                source_profile="universal",
            ),
        ],
        stats={"llm_calls": 1},
    )


def _empty_result() -> AuditResult:
    return AuditResult(profiles_used=["universal"], files_analyzed=["A.sol"])


# ─── adapter registry ─────────────────────────────────────────────────────


def test_all_four_formats_registered() -> None:
    assert set(available_formats()) >= {"markdown", "json", "sarif", "forefy"}


def test_emit_dispatches_correctly() -> None:
    r = _empty_result()
    md = emit(r, "markdown")
    assert "drozer-lite" in md


def test_emit_unknown_format_raises() -> None:
    with pytest.raises(ValueError, match="Unknown output format"):
        emit(_empty_result(), "yaml")


# ─── markdown ─────────────────────────────────────────────────────────────


def test_markdown_includes_header_and_summary() -> None:
    md = format_markdown(_result_with_findings())
    assert "# drozer-lite" in md
    assert "Summary" in md
    assert "Vault.sol" in md


def test_markdown_sorts_critical_before_high() -> None:
    md = format_markdown(_result_with_findings())
    crit_pos = md.find("CRITICAL")
    high_pos = md.find("HIGH")
    assert crit_pos < high_pos


# ─── json ─────────────────────────────────────────────────────────────────


def test_json_is_valid_json() -> None:
    out = format_json(_result_with_findings())
    parsed = json.loads(out)
    assert parsed["scanner"] == "drozer-lite"
    assert len(parsed["findings"]) == 2


def test_json_strips_none_fields() -> None:
    out = format_json(_result_with_findings())
    parsed = json.loads(out)
    # None-valued line_hint or original_type should not appear.
    for f in parsed["findings"]:
        for v in f.values():
            assert v is not None


def test_json_empty_findings() -> None:
    out = format_json(_empty_result())
    parsed = json.loads(out)
    assert parsed["findings"] == []


# ─── sarif ────────────────────────────────────────────────────────────────


def test_sarif_top_level_shape() -> None:
    out = format_sarif(_result_with_findings())
    parsed = json.loads(out)
    assert parsed["version"] == "2.1.0"
    assert len(parsed["runs"]) == 1
    run = parsed["runs"][0]
    assert run["tool"]["driver"]["name"] == "drozer-lite"


def test_sarif_severity_to_level_mapping() -> None:
    out = format_sarif(_result_with_findings())
    parsed = json.loads(out)
    levels = [r["level"] for r in parsed["runs"][0]["results"]]
    assert "error" in levels  # CRITICAL + HIGH


def test_sarif_rules_emitted_for_each_unique_type() -> None:
    out = format_sarif(_result_with_findings())
    parsed = json.loads(out)
    rule_ids = [r["id"] for r in parsed["runs"][0]["tool"]["driver"]["rules"]]
    assert "reentrancy" in rule_ids
    assert "missing_access_control" in rule_ids


def test_sarif_swc_help_uri_emitted() -> None:
    out = format_sarif(_result_with_findings())
    parsed = json.loads(out)
    rules = parsed["runs"][0]["tool"]["driver"]["rules"]
    reentrancy = next(r for r in rules if r["id"] == "reentrancy")
    assert "swcregistry.io" in reentrancy.get("helpUri", "")


def test_sarif_empty_findings() -> None:
    out = format_sarif(_empty_result())
    parsed = json.loads(out)
    assert parsed["runs"][0]["results"] == []


# ─── forefy ───────────────────────────────────────────────────────────────


def test_forefy_lowercase_severity() -> None:
    out = format_forefy(_result_with_findings())
    parsed = json.loads(out)
    severities = [f["severity"] for f in parsed["findings"]]
    assert all(s.islower() for s in severities)


def test_forefy_canonical_vulnerability_type() -> None:
    r = _result_with_findings()
    r.findings[0].vulnerability_type = "CEI violation"
    out = format_forefy(r)
    parsed = json.loads(out)
    types = {f["vulnerability_type"] for f in parsed["findings"]}
    assert "reentrancy" in types


def test_forefy_skips_non_representatives() -> None:
    r = _result_with_findings()
    # Mark one as a non-representative; forefy should drop it.
    setattr(r.findings[0], "is_cluster_representative", False)
    setattr(r.findings[1], "is_cluster_representative", True)
    out = format_forefy(r)
    parsed = json.loads(out)
    assert len(parsed["findings"]) == 1


def test_forefy_empty_findings() -> None:
    out = format_forefy(_empty_result())
    parsed = json.loads(out)
    assert parsed["findings"] == []
