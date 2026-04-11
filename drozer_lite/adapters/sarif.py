"""SARIF v2.1.0 output adapter — for GitHub code scanning and CI integration.

Reference: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html

drozer-lite emits ONE SARIF run per audit. Each unique vulnerability_type
becomes a SARIF rule (with optional SWC/CWE help URLs); each finding
becomes a SARIF result referencing that rule.
"""

from __future__ import annotations

import json

from drozer_lite.audit import AuditResult, Finding
from drozer_lite.vocab import canonicalize, lookup

SARIF_VERSION = "2.1.0"
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"

_LEVEL_MAP = {
    "CRITICAL": "error",
    "HIGH": "error",
    "MEDIUM": "warning",
    "LOW": "note",
    "INFO": "note",
}


def _level(severity: str) -> str:
    return _LEVEL_MAP.get((severity or "").upper(), "warning")


def _help_uri(swc_id: str | None) -> str | None:
    if not swc_id:
        return None
    num = swc_id.replace("SWC-", "")
    return f"https://swcregistry.io/docs/SWC-{num}"


def _build_rules(findings: list[Finding]) -> list[dict]:
    seen: dict[str, dict] = {}
    for f in findings:
        canonical, _ = canonicalize(f.vulnerability_type)
        rule_id = canonical or f.vulnerability_type
        if rule_id in seen:
            continue
        entry = lookup(canonical)
        rule = {
            "id": rule_id,
            "name": rule_id,
            "shortDescription": {
                "text": entry.description if entry else f.vulnerability_type,
            },
            "fullDescription": {
                "text": entry.description if entry else f.vulnerability_type,
            },
            "defaultConfiguration": {"level": _level(f.severity)},
        }
        if entry and entry.swc_id:
            help_uri = _help_uri(entry.swc_id)
            if help_uri:
                rule["helpUri"] = help_uri
        if entry and entry.cwe_id:
            rule["properties"] = {"tags": [entry.cwe_id]}
        seen[rule_id] = rule
    return list(seen.values())


def _build_result(f: Finding) -> dict:
    canonical, _ = canonicalize(f.vulnerability_type)
    region: dict = {}
    if f.line_hint:
        region["startLine"] = f.line_hint

    location: dict = {
        "physicalLocation": {
            "artifactLocation": {"uri": f.affected_file},
        }
    }
    if region:
        location["physicalLocation"]["region"] = region

    return {
        "ruleId": canonical or f.vulnerability_type,
        "level": _level(f.severity),
        "message": {
            "text": f"{f.affected_function}: {f.explanation}",
        },
        "locations": [location],
        "properties": {
            "severity": f.severity,
            "confidence": f.confidence,
            "source_profile": f.source_profile,
        },
    }


def format_sarif(result: AuditResult) -> str:
    rules = _build_rules(result.findings)
    results = [_build_result(f) for f in result.findings]
    sarif = {
        "$schema": SARIF_SCHEMA,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": result.scanner,
                        "version": result.version,
                        "informationUri": "https://github.com/gdroz3r/drozer-lite",
                        "rules": rules,
                    }
                },
                "results": results,
                "invocations": [
                    {
                        "executionSuccessful": not bool(
                            [w for w in result.warnings if "failed" in w.lower()]
                        ),
                    }
                ],
            }
        ],
    }
    return json.dumps(sarif, indent=2)
