"""Fixture loader and structural validator.

The fixture corpus lives in `tests/fixtures/<profile>/{vulnerable,clean}.sol`
plus a top-level `expectations.json` that pins, for each fixture, the
profile and the canonical vulnerability_type the LLM should report on the
vulnerable case.

This module is import-safe (no LLM calls) so it can be used both by:
- the unit test suite (`test_fixtures.py`) for structural validation
- the benchmark runner (Phase 6) for end-to-end validation against a
  real or mocked LLM
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
EXPECTATIONS_PATH = FIXTURES_DIR / "expectations.json"


class FixtureError(Exception):
    """Raised when a fixture is missing or malformed."""


@dataclass(frozen=True)
class FixtureCase:
    profile: str
    auto_detect: bool
    vulnerable_type: str
    vulnerable_function: str
    vulnerable_path: Path
    clean_path: Path

    def vulnerable_source(self) -> str:
        return self.vulnerable_path.read_text(encoding="utf-8")

    def clean_source(self) -> str:
        return self.clean_path.read_text(encoding="utf-8")


def load_fixtures() -> list[FixtureCase]:
    """Load every fixture defined in expectations.json.

    Raises FixtureError if a referenced fixture file is missing.
    """
    if not EXPECTATIONS_PATH.is_file():
        raise FixtureError(f"expectations.json not found at {EXPECTATIONS_PATH}")

    payload = json.loads(EXPECTATIONS_PATH.read_text(encoding="utf-8"))
    cases: list[FixtureCase] = []
    for entry in payload.get("fixtures", []):
        profile = entry["profile"]
        vulnerable_path = FIXTURES_DIR / profile / "vulnerable.sol"
        clean_path = FIXTURES_DIR / profile / "clean.sol"
        if not vulnerable_path.is_file():
            raise FixtureError(f"missing vulnerable fixture for {profile}: {vulnerable_path}")
        if not clean_path.is_file():
            raise FixtureError(f"missing clean fixture for {profile}: {clean_path}")
        cases.append(
            FixtureCase(
                profile=profile,
                auto_detect=bool(entry.get("auto_detect", True)),
                vulnerable_type=entry["vulnerable_type"],
                vulnerable_function=entry["vulnerable_function"],
                vulnerable_path=vulnerable_path,
                clean_path=clean_path,
            )
        )
    return cases
