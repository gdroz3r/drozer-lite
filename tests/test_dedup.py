"""Tests for dedup.py — structural clustering."""

from __future__ import annotations

from drozer_lite.audit import Finding
from drozer_lite.dedup import dedup_findings


def _f(t, fn, file, sev="MEDIUM"):
    return Finding(
        vulnerability_type=t,
        affected_function=fn,
        affected_file=file,
        severity=sev,
        explanation="x",
    )


def test_dedup_empty() -> None:
    out, stats = dedup_findings([])
    assert out == []
    assert stats.total_findings == 0


def test_singleton_is_its_own_representative() -> None:
    out, stats = dedup_findings([_f("reentrancy", "withdraw", "A.sol")])
    assert len(out) == 1
    assert out[0].is_cluster_representative is True
    assert out[0].cluster_size == 1
    assert stats.merged_away == 0


def test_two_findings_same_class_same_loc_cluster() -> None:
    a = _f("reentrancy", "withdraw", "A.sol", "HIGH")
    b = _f("reentrancy", "withdraw", "A.sol", "MEDIUM")
    out, stats = dedup_findings([a, b])
    assert len(out) == 2
    assert stats.merged_away == 1
    assert stats.clusters == 1
    # Highest-severity is the representative.
    rep = next(f for f in out if f.is_cluster_representative)
    assert rep.severity == "HIGH"


def test_synonym_collapses_into_canonical() -> None:
    a = _f("reentrancy", "withdraw", "A.sol", "HIGH")
    b = _f("CEI violation", "withdraw", "A.sol", "MEDIUM")
    out, stats = dedup_findings([a, b])
    assert stats.clusters == 1
    assert stats.merged_away == 1


def test_different_function_does_not_cluster() -> None:
    a = _f("reentrancy", "withdraw", "A.sol")
    b = _f("reentrancy", "deposit", "A.sol")
    out, stats = dedup_findings([a, b])
    assert stats.clusters == 2
    assert stats.merged_away == 0


def test_different_file_does_not_cluster() -> None:
    a = _f("reentrancy", "withdraw", "A.sol")
    b = _f("reentrancy", "withdraw", "B.sol")
    out, stats = dedup_findings([a, b])
    assert stats.clusters == 2


def test_representatives_sorted_first() -> None:
    a = _f("reentrancy", "f", "A.sol", "LOW")
    b = _f("reentrancy", "f", "A.sol", "CRITICAL")
    c = _f("missing_access_control", "g", "B.sol", "HIGH")
    out, stats = dedup_findings([a, b, c])
    assert out[0].is_cluster_representative is True
    assert out[0].severity == "CRITICAL"  # highest sev rep first
    assert out[1].is_cluster_representative is True
    assert out[1].severity == "HIGH"


def test_largest_cluster_recorded() -> None:
    findings = [_f("reentrancy", "withdraw", "A.sol") for _ in range(5)]
    findings.append(_f("integer_overflow", "deposit", "B.sol"))
    _, stats = dedup_findings(findings)
    assert stats.largest_cluster == 5
