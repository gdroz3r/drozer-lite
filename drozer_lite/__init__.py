"""drozer-lite: Fast, deterministic Solidity pattern scanner.

Public API:

    from drozer_lite import audit_path, audit_source

    result = audit_path("MyContract.sol")
    for finding in result.findings:
        print(finding.vulnerability_type, finding.affected_function)

See README.md for full usage.
"""

from drozer_lite.audit import AuditResult, Finding, audit_path, audit_source

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "audit_path",
    "audit_source",
    "AuditResult",
    "Finding",
]
