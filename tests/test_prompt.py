"""Tests for prompt.py — pure assembly, no LLM."""

from __future__ import annotations

import json

from drozer_lite.prompt import SCHEMA_PATH, build_prompt


def test_build_prompt_returns_system_and_user() -> None:
    out = build_prompt(
        checklist="## Checks\n\n### CHECK-1: foo\n",
        files=[("A.sol", "contract A {}")],
        profiles_used=["universal"],
    )
    assert out.system
    assert out.user
    assert out.system != out.user


def test_system_contains_checklist_and_schema() -> None:
    out = build_prompt(
        checklist="UNIQUE_CHECKLIST_TOKEN",
        files=[("A.sol", "x")],
        profiles_used=["universal"],
    )
    assert "UNIQUE_CHECKLIST_TOKEN" in out.system
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["title"] in out.system or "drozer-lite native output" in out.system


def test_user_contains_all_files() -> None:
    out = build_prompt(
        checklist="x",
        files=[("A.sol", "ALPHA"), ("B.sol", "BETA")],
        profiles_used=["universal"],
    )
    assert "A.sol" in out.user
    assert "B.sol" in out.user
    assert "ALPHA" in out.user
    assert "BETA" in out.user


def test_user_lists_profiles() -> None:
    out = build_prompt(
        checklist="x",
        files=[("A.sol", "x")],
        profiles_used=["universal", "vault", "lending"],
    )
    assert "universal" in out.user
    assert "vault" in out.user
    assert "lending" in out.user


def test_build_prompt_is_deterministic() -> None:
    args = dict(
        checklist="abc",
        files=[("A.sol", "x")],
        profiles_used=["universal"],
    )
    a = build_prompt(**args)
    b = build_prompt(**args)
    assert a.system == b.system
    assert a.user == b.user
