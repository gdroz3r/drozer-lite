"""Benchmark runner — score drozer-lite against the fixture corpus.

For each fixture case (vulnerable + clean Solidity pair):

  * Run audit_source on the vulnerable file.
    - PASS if at least one finding's canonical vulnerability_type matches
      `expected.vulnerable_type` AND its affected_function matches
      `expected.vulnerable_function`.
    - FAIL otherwise.
  * Run audit_source on the clean file.
    - CLEAN if no finding matches `expected.vulnerable_type`.
    - NOISY if any does.

A `BenchmarkReport` aggregates per-fixture rows and totals. The benchmark
runner does NOT call the LLM directly — it goes through `audit.audit_source`
just like a normal user would, so the same caching, validation, and dedup
apply. Tests can mock at the `audit.llm.call_llm` boundary.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from drozer_lite import audit
from drozer_lite.fixtures import FixtureCase, load_fixtures
from drozer_lite.vocab import canonicalize


@dataclass
class FixtureResult:
    profile: str
    expected_type: str
    expected_function: str
    vulnerable_pass: bool
    clean_clean: bool
    vulnerable_findings: int
    clean_findings: int
    vulnerable_warnings: list[str] = field(default_factory=list)
    clean_warnings: list[str] = field(default_factory=list)
    matched_finding: str | None = None
    elapsed_sec: float = 0.0


@dataclass
class BenchmarkReport:
    rows: list[FixtureResult] = field(default_factory=list)
    total: int = 0
    vulnerable_passed: int = 0
    clean_clean: int = 0
    started_at: float = 0.0
    wall_time_sec: float = 0.0

    @property
    def precision(self) -> float:
        return self.vulnerable_passed / self.total if self.total else 0.0

    @property
    def cleanliness(self) -> float:
        return self.clean_clean / self.total if self.total else 0.0


def _vulnerable_match(
    findings: list[audit.Finding], expected_type: str, expected_function: str
) -> audit.Finding | None:
    canonical_expected, _ = canonicalize(expected_type)
    for f in findings:
        canonical_actual, _ = canonicalize(f.vulnerability_type)
        if canonical_actual != canonical_expected:
            continue
        if expected_function and expected_function.lower() not in (
            f.affected_function or ""
        ).lower():
            continue
        return f
    return None


def _clean_has_match(findings: list[audit.Finding], expected_type: str) -> bool:
    canonical_expected, _ = canonicalize(expected_type)
    for f in findings:
        canonical_actual, _ = canonicalize(f.vulnerability_type)
        if canonical_actual == canonical_expected:
            return True
    return False


def run_benchmark(
    cases: list[FixtureCase] | None = None,
    *,
    model: str = audit.llm.DEFAULT_MODEL,
) -> BenchmarkReport:
    """Score drozer-lite against the fixture corpus.

    `cases` defaults to `load_fixtures()`. Returns a BenchmarkReport.
    Each case results in two LLM calls (one vulnerable, one clean).
    """
    if cases is None:
        cases = load_fixtures()

    report = BenchmarkReport(started_at=time.time())
    started = time.monotonic()

    for case in cases:
        case_started = time.monotonic()
        profile_override = None if case.auto_detect else case.profile

        vuln_files = [(case.vulnerable_path.name, case.vulnerable_source())]
        vuln_result = audit.audit_source(vuln_files, profile=profile_override, model=model)
        matched = _vulnerable_match(vuln_result.findings, case.vulnerable_type, case.vulnerable_function)

        clean_files = [(case.clean_path.name, case.clean_source())]
        clean_result = audit.audit_source(clean_files, profile=profile_override, model=model)
        clean_match = _clean_has_match(clean_result.findings, case.vulnerable_type)

        row = FixtureResult(
            profile=case.profile,
            expected_type=case.vulnerable_type,
            expected_function=case.vulnerable_function,
            vulnerable_pass=matched is not None,
            clean_clean=not clean_match,
            vulnerable_findings=len(vuln_result.findings),
            clean_findings=len(clean_result.findings),
            vulnerable_warnings=list(vuln_result.warnings),
            clean_warnings=list(clean_result.warnings),
            matched_finding=(matched.affected_function if matched else None),
            elapsed_sec=round(time.monotonic() - case_started, 2),
        )
        report.rows.append(row)
        report.total += 1
        if row.vulnerable_pass:
            report.vulnerable_passed += 1
        if row.clean_clean:
            report.clean_clean += 1

    report.wall_time_sec = round(time.monotonic() - started, 2)
    return report


def format_report(report: BenchmarkReport) -> str:
    """Format a BenchmarkReport as a human-readable Markdown table."""
    lines: list[str] = []
    lines.append("# drozer-lite benchmark report\n")
    lines.append(
        f"**Total cases**: {report.total}  \n"
        f"**Vulnerable detection rate**: "
        f"{report.vulnerable_passed}/{report.total} "
        f"({report.precision * 100:.0f}%)  \n"
        f"**Clean cleanliness rate**: "
        f"{report.clean_clean}/{report.total} "
        f"({report.cleanliness * 100:.0f}%)  \n"
        f"**Wall time**: {report.wall_time_sec}s\n"
    )
    lines.append(
        "| Profile | Expected type | V detected | Clean | V findings | "
        "Clean findings | Time (s) |"
    )
    lines.append(
        "|---------|---------------|------------|-------|------------|"
        "----------------|----------|"
    )
    for r in report.rows:
        v = "PASS" if r.vulnerable_pass else "MISS"
        c = "CLEAN" if r.clean_clean else "NOISY"
        lines.append(
            f"| {r.profile} | `{r.expected_type}` | {v} | {c} | "
            f"{r.vulnerable_findings} | {r.clean_findings} | {r.elapsed_sec} |"
        )
    return "\n".join(lines) + "\n"
