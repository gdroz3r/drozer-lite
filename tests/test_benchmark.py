"""Tests for the benchmark runner — uses a mocked LLM, no real API calls."""

from __future__ import annotations

import json

import pytest

from drozer_lite import audit, llm
from drozer_lite.benchmark import format_report, run_benchmark
from drozer_lite.fixtures import FixtureCase, load_fixtures


def _resp(payload: dict) -> llm.LLMResponse:
    return llm.LLMResponse(
        text=json.dumps(payload),
        model="mock",
        input_tokens=10,
        output_tokens=10,
        cached_tokens=0,
        retries=0,
    )


def _identify_case(user_prompt: str) -> tuple[FixtureCase | None, bool]:
    """Match the user prompt to the fixture case it represents.

    Returns (case, is_clean). Matches by source content snippet — every
    fixture has a unique contract definition line, so this is reliable
    even though all fixtures share the same `vulnerable.sol` / `clean.sol`
    basename."""
    cases = load_fixtures()
    for case in cases:
        if case.vulnerable_source() in user_prompt:
            return case, False
        if case.clean_source() in user_prompt:
            return case, True
    return None, False


@pytest.fixture
def all_pass(monkeypatch):
    """Mock that returns the expected finding for the vulnerable file
    and zero findings for the clean file."""

    def fake(*, system, user, **kw):
        case, is_clean = _identify_case(user)
        if case is None or is_clean:
            return _resp({"scanner": "drozer-lite", "version": "0.1.0", "findings": []})
        return _resp({
            "scanner": "drozer-lite",
            "version": "0.1.0",
            "findings": [
                {
                    "vulnerability_type": case.vulnerable_type,
                    "affected_function": case.vulnerable_function,
                    "affected_file": case.vulnerable_path.name,
                    "severity": "HIGH",
                    "explanation": "test",
                    "source_profile": case.profile,
                }
            ],
        })

    monkeypatch.setattr(audit.llm, "call_llm", fake)


@pytest.fixture
def all_miss(monkeypatch):
    """Mock that returns zero findings for everything."""
    def fake(*, system, user, **kw):
        return _resp({"scanner": "drozer-lite", "version": "0.1.0", "findings": []})
    monkeypatch.setattr(audit.llm, "call_llm", fake)


@pytest.fixture
def noisy_clean(monkeypatch):
    """Mock that returns the expected finding for BOTH vulnerable and clean
    files — clean cases should therefore be marked NOISY."""
    def fake(*, system, user, **kw):
        case, is_clean = _identify_case(user)
        if case is None:
            return _resp({"scanner": "drozer-lite", "version": "0.1.0", "findings": []})
        path = case.clean_path.name if is_clean else case.vulnerable_path.name
        return _resp({
            "scanner": "drozer-lite",
            "version": "0.1.0",
            "findings": [
                {
                    "vulnerability_type": case.vulnerable_type,
                    "affected_function": case.vulnerable_function,
                    "affected_file": path,
                    "severity": "HIGH",
                    "explanation": "test",
                    "source_profile": case.profile,
                }
            ],
        })
    monkeypatch.setattr(audit.llm, "call_llm", fake)


def test_benchmark_perfect_run(all_pass) -> None:
    report = run_benchmark()
    assert report.total >= 11
    assert report.vulnerable_passed == report.total
    assert report.clean_clean == report.total
    assert report.precision == 1.0
    assert report.cleanliness == 1.0


def test_benchmark_all_miss(all_miss) -> None:
    report = run_benchmark()
    assert report.vulnerable_passed == 0
    assert report.clean_clean == report.total  # nothing returned for clean either
    assert report.precision == 0.0


def test_benchmark_noisy_clean(noisy_clean) -> None:
    report = run_benchmark()
    assert report.vulnerable_passed == report.total
    assert report.clean_clean == 0  # every clean case is noisy


def test_format_report_renders_table(all_pass) -> None:
    report = run_benchmark()
    md = format_report(report)
    assert "drozer-lite benchmark report" in md
    assert "Profile" in md
    assert "PASS" in md
    assert "CLEAN" in md


def test_benchmark_includes_every_fixture(all_pass) -> None:
    report = run_benchmark()
    profiles_in_report = {row.profile for row in report.rows}
    profiles_expected = {case.profile for case in load_fixtures()}
    assert profiles_in_report == profiles_expected


def test_benchmark_with_subset(all_pass) -> None:
    cases = load_fixtures()[:3]
    report = run_benchmark(cases=cases)
    assert report.total == 3
