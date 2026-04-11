"""Tests for checklist loading and assembly."""

from __future__ import annotations

import pytest

from drozer_lite.checklist import (
    CHECKLIST_DIR,
    ChecklistNotFoundError,
    available_profiles,
    load_checklist,
)


def test_available_profiles_finds_thirteen() -> None:
    profiles = available_profiles()
    expected = {
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
    }
    assert expected.issubset(set(profiles))


def test_load_checklist_universal_only() -> None:
    out = load_checklist(["universal"])
    assert "universal" in out.lower()
    assert len(out) > 1000  # universal is large


def test_load_checklist_prepends_universal() -> None:
    out = load_checklist(["vault"])
    universal_text = (CHECKLIST_DIR / "universal.md").read_text(encoding="utf-8")
    vault_text = (CHECKLIST_DIR / "vault.md").read_text(encoding="utf-8")
    assert out.find(universal_text[:200]) < out.find(vault_text[:200])


def test_load_checklist_dedupes_universal() -> None:
    a = load_checklist(["vault"])
    b = load_checklist(["universal", "vault"])
    assert a == b


def test_load_checklist_preserves_order_after_universal() -> None:
    out = load_checklist(["vault", "lending"])
    vault_text = (CHECKLIST_DIR / "vault.md").read_text(encoding="utf-8")
    lending_text = (CHECKLIST_DIR / "lending.md").read_text(encoding="utf-8")
    assert out.find(vault_text[:200]) < out.find(lending_text[:200])


def test_load_checklist_unknown_profile_raises() -> None:
    with pytest.raises(ChecklistNotFoundError):
        load_checklist(["nonexistent_profile"])


def test_load_checklist_explicit_only_profile_loads() -> None:
    out = load_checklist(["icp"])
    icp_text = (CHECKLIST_DIR / "icp.md").read_text(encoding="utf-8")
    assert icp_text[:200] in out
