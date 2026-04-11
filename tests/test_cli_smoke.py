"""Smoke tests for the CLI entry point.

These run against the Build Phase 1 scaffold — they verify the CLI is
wired correctly, flags parse, and subcommands dispatch without crashing.
They do NOT exercise the audit pipeline yet (that lands in Phase 3).
"""

from __future__ import annotations

import subprocess
import sys

import pytest


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Invoke the drozer-lite CLI via the installed entry point."""
    return subprocess.run(
        [sys.executable, "-m", "drozer_lite.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_version() -> None:
    result = run_cli("--version")
    assert result.returncode == 0
    assert "drozer-lite" in result.stdout


def test_help_root() -> None:
    result = run_cli("--help")
    assert result.returncode == 0
    assert "audit" in result.stdout
    assert "list-profiles" in result.stdout


def test_help_audit() -> None:
    result = run_cli("audit", "--help")
    assert result.returncode == 0
    assert "--format" in result.stdout
    assert "--profile" in result.stdout


def test_list_profiles() -> None:
    result = run_cli("list-profiles")
    assert result.returncode == 0
    # All 13 profiles should appear
    for profile in (
        "universal",
        "signature",
        "vault",
        "lending",
        "dex",
        "cross-chain",
        "governance",
        "reentrancy",
        "oracle",
        "math",
        "gaming",
        "icp",
        "solana",
    ):
        assert profile in result.stdout
    assert "always loaded" in result.stdout
    assert "explicit-only" in result.stdout


def test_audit_missing_path() -> None:
    """Audit against a nonexistent path must exit 2."""
    result = run_cli("audit", "/nonexistent/path/to/file.sol")
    assert result.returncode == 2


def test_audit_rejects_unknown_format() -> None:
    result = run_cli("audit", "foo.sol", "--format", "xml")
    assert result.returncode != 0
    assert "invalid choice" in result.stderr.lower()


def test_audit_rejects_unknown_profile() -> None:
    result = run_cli("audit", "foo.sol", "--profile", "quantum")
    assert result.returncode != 0
    assert "invalid choice" in result.stderr.lower()


@pytest.mark.parametrize("fmt", ["markdown", "json", "sarif", "forefy"])
def test_audit_accepts_all_declared_formats(fmt: str, tmp_path) -> None:
    """Format flag parses for every format we claim to support."""
    dummy = tmp_path / "dummy.sol"
    dummy.write_text("// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\ncontract Dummy {}\n")
    result = run_cli("audit", str(dummy), "--format", fmt)
    # Scaffold should return 0 — it's not running the audit pipeline yet.
    assert result.returncode == 0
