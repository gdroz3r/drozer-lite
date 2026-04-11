"""End-to-end audit tests with the LLM mocked.

These exercise the full audit_source / audit_path pipeline without making
any real Anthropic API calls. The LLM client is monkeypatched at the
drozer_lite.llm.call_llm boundary so the rest of the stack runs untouched.
"""

from __future__ import annotations

import json

import pytest

from drozer_lite import audit, llm
from drozer_lite.adapters.markdown import format_markdown


VAULT_SOURCE = """\
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MyVault is ERC4626 {
    function deposit(uint256 a) public {}
    function withdraw(uint256 a) public {}
    function totalAssets() public view returns (uint256) {}
    function previewDeposit(uint256 a) public view returns (uint256) {}
    function convertToShares(uint256 a) public view returns (uint256) {}
}
"""


def _fake_llm_response(payload: dict) -> llm.LLMResponse:
    return llm.LLMResponse(
        text=json.dumps(payload),
        model="mock",
        input_tokens=100,
        output_tokens=50,
        cached_tokens=0,
        retries=0,
    )


@pytest.fixture
def mock_llm(monkeypatch):
    """Replace llm.call_llm with a function that returns a canned payload.

    Tests can set `mock_llm.payload = {...}` to control what comes back.
    """
    state = {"payload": {
        "scanner": "drozer-lite",
        "version": "0.1.0",
        "findings": [],
    }}

    def fake_call(*, system, user, model="mock", max_tokens=4000, timeout=180):
        # Sanity: ensure the prompt builder fed something through.
        assert system
        assert user
        return _fake_llm_response(state["payload"])

    monkeypatch.setattr(audit.llm, "call_llm", fake_call)
    return state


def test_audit_source_no_findings(mock_llm) -> None:
    result = audit.audit_source(
        [("MyVault.sol", VAULT_SOURCE)],
        profile="auto",
    )
    assert result.scanner == "drozer-lite"
    assert "universal" in result.profiles_used
    assert "vault" in result.profiles_used
    assert result.files_analyzed == ["MyVault.sol"]
    assert result.findings == []
    assert result.stats["llm_calls"] == 1


def test_audit_source_with_finding(mock_llm) -> None:
    mock_llm["payload"] = {
        "scanner": "drozer-lite",
        "version": "0.1.0",
        "findings": [
            {
                "vulnerability_type": "share_inflation",
                "affected_function": "deposit",
                "affected_file": "MyVault.sol",
                "severity": "HIGH",
                "explanation": "First-depositor share inflation.",
                "line_hint": 5,
                "confidence": "HIGH",
                "source_profile": "vault",
            }
        ],
    }
    result = audit.audit_source(
        [("MyVault.sol", VAULT_SOURCE)],
        profile="auto",
    )
    assert len(result.findings) == 1
    f = result.findings[0]
    assert f.vulnerability_type == "share_inflation"
    assert f.severity == "HIGH"
    assert f.source_profile == "vault"


def test_audit_source_explicit_profile_override(mock_llm) -> None:
    result = audit.audit_source(
        [("Whatever.sol", "contract X {}")],
        profile="lending",
    )
    assert "lending" in result.profiles_used
    assert "universal" in result.profiles_used


def test_audit_source_explicit_only_profile(mock_llm) -> None:
    result = audit.audit_source(
        [("anchor_program.rs", "fn main() {}")],
        profile="solana",
    )
    assert "solana" in result.profiles_used


def test_audit_path_directory(tmp_path, mock_llm) -> None:
    (tmp_path / "Vault.sol").write_text(VAULT_SOURCE)
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "Excluded.sol").write_text("contract Excluded {}")
    result = audit.audit_path(tmp_path, max_bytes=100_000)
    assert result.files_analyzed == ["Vault.sol"]
    assert "vault" in result.profiles_used


def test_audit_path_excludes_test_dirs(tmp_path, mock_llm) -> None:
    (tmp_path / "Real.sol").write_text("contract Real {}")
    (tmp_path / "test").mkdir()
    (tmp_path / "test" / "TestThing.sol").write_text("contract Test {}")
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "Lib.sol").write_text("contract Lib {}")
    result = audit.audit_path(tmp_path, max_bytes=100_000)
    assert result.files_analyzed == ["Real.sol"]


def test_audit_path_max_bytes(tmp_path, mock_llm) -> None:
    big = "x" * 50_000
    (tmp_path / "Big.sol").write_text(f"contract Big {{ string c = \"{big}\"; }}")
    result = audit.audit_path(tmp_path, max_bytes=10_000)
    assert result.files_analyzed == []
    assert any("max_bytes" in w for w in result.warnings)


def test_audit_path_nonexistent(tmp_path, mock_llm) -> None:
    result = audit.audit_path(tmp_path / "nope.sol")
    assert result.files_analyzed == []
    assert any("does not exist" in w for w in result.warnings)


def test_audit_handles_llm_failure(monkeypatch) -> None:
    def fail(*, system, user, **kw):
        raise llm.LLMError("simulated")

    monkeypatch.setattr(audit.llm, "call_llm", fail)
    result = audit.audit_source([("A.sol", "contract A {}")])
    assert any("LLM call failed" in w for w in result.warnings)
    assert result.findings == []


def test_audit_handles_schema_failure(monkeypatch) -> None:
    def bad(*, system, user, **kw):
        return llm.LLMResponse(
            text="not json",
            model="mock",
            input_tokens=0,
            output_tokens=0,
            cached_tokens=0,
            retries=0,
        )

    monkeypatch.setattr(audit.llm, "call_llm", bad)
    result = audit.audit_source([("A.sol", "contract A {}")])
    assert any("schema validation failed" in w for w in result.warnings)


def test_markdown_adapter_formats_no_findings(mock_llm) -> None:
    result = audit.audit_source([("A.sol", "contract A {}")])
    md = format_markdown(result)
    assert "drozer-lite" in md
    assert "Summary" in md
    assert "No findings" in md


def test_markdown_adapter_formats_with_findings(mock_llm) -> None:
    mock_llm["payload"] = {
        "scanner": "drozer-lite",
        "version": "0.1.0",
        "findings": [
            {
                "vulnerability_type": "reentrancy",
                "affected_function": "withdraw",
                "affected_file": "A.sol",
                "severity": "HIGH",
                "explanation": "Test.",
                "line_hint": 1,
                "confidence": "HIGH",
                "source_profile": "reentrancy",
            }
        ],
    }
    result = audit.audit_source([("A.sol", "contract A {}")])
    md = format_markdown(result)
    assert "reentrancy" in md
    assert "HIGH" in md
    assert "withdraw" in md
