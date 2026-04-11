"""Structural tests for the fixture corpus.

These do NOT call the LLM. They verify:
- every entry in expectations.json has a vulnerable.sol and clean.sol on disk
- both files parse minimally (have a contract definition)
- the vulnerable_type is in the canonical vocabulary
- detect.detect_profiles auto-detects the expected profile (when
  auto_detect=true) — gives early warning if a regex pattern set drifts
  away from a fixture
"""

from __future__ import annotations

import re

import pytest

from drozer_lite.detect import detect_profiles
from drozer_lite.fixtures import load_fixtures
from drozer_lite.vocab import canonicalize


@pytest.fixture(scope="module")
def fixtures():
    return load_fixtures()


def test_at_least_eleven_fixtures(fixtures) -> None:
    assert len(fixtures) >= 11


def test_each_fixture_has_a_contract(fixtures) -> None:
    for case in fixtures:
        for src in (case.vulnerable_source(), case.clean_source()):
            assert re.search(r"\bcontract\s+\w+", src), f"no contract in {case.profile}"


def test_each_vulnerable_type_is_canonical(fixtures) -> None:
    for case in fixtures:
        canonical, mapped = canonicalize(case.vulnerable_type)
        assert mapped, (
            f"{case.profile}: vulnerable_type {case.vulnerable_type!r} "
            f"is not in vocab.VOCABULARY or its synonym map"
        )


def test_auto_detect_profiles(fixtures) -> None:
    for case in fixtures:
        if not case.auto_detect:
            continue
        files = [(case.vulnerable_path.name, case.vulnerable_source())]
        sel = detect_profiles(files)
        assert case.profile in sel.selected, (
            f"{case.profile} fixture should auto-detect into {case.profile} "
            f"but selection was {sel.selected} with scores {sel.scores}"
        )


def test_clean_and_vulnerable_differ(fixtures) -> None:
    for case in fixtures:
        assert case.vulnerable_source() != case.clean_source(), (
            f"{case.profile}: clean and vulnerable fixtures are identical"
        )
