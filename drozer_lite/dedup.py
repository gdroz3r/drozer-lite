"""Inline root-cause deduplication.

drozer-lite findings are already structured (vulnerability_type +
affected_file + affected_function), so dedup is much simpler than the
text-pattern clustering used by the full drozer pipeline. We cluster on:

    (canonical_vulnerability_type, affected_file, affected_function)

The highest-severity finding in each cluster is the representative.
Following the same philosophy as the main drozer dedup harness, we tag
findings rather than delete them — the caller can filter by
`is_cluster_representative` if a flat list is desired.

Returns the same list of Finding objects, mutated in-place to add
cluster metadata, sorted so representatives come first.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from drozer_lite.audit import Finding
from drozer_lite.vocab import canonicalize

SEVERITY_RANK = {
    "CRITICAL": 5,
    "HIGH": 4,
    "MEDIUM": 3,
    "LOW": 2,
    "INFO": 1,
}


@dataclass
class DedupStats:
    total_findings: int
    representatives: int
    merged_away: int
    clusters: int
    largest_cluster: int


def _cluster_key(f: Finding) -> tuple[str, str, str]:
    canonical, _ = canonicalize(f.vulnerability_type)
    return (canonical, f.affected_file or "?", f.affected_function or "?")


def _severity_rank(f: Finding) -> int:
    return SEVERITY_RANK.get((f.severity or "").upper(), 0)


def dedup_findings(findings: list[Finding]) -> tuple[list[Finding], DedupStats]:
    """Cluster findings by structural key, tag in place, return tagged list.

    The returned list is sorted: representatives first (by descending
    severity), then non-representatives grouped by cluster_id.
    """
    if not findings:
        return [], DedupStats(0, 0, 0, 0, 0)

    clusters: dict[tuple[str, str, str], list[Finding]] = defaultdict(list)
    for f in findings:
        clusters[_cluster_key(f)].append(f)

    stats = DedupStats(
        total_findings=len(findings),
        representatives=0,
        merged_away=0,
        clusters=len(clusters),
        largest_cluster=0,
    )

    cluster_id = 0
    for key, group in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
        cluster_id += 1
        stats.largest_cluster = max(stats.largest_cluster, len(group))

        # Representative = highest severity, ties broken by stable order.
        group.sort(key=lambda f: -_severity_rank(f))
        rep = group[0]
        rep_setattr = lambda obj, k, v: object.__setattr__(obj, k, v) if hasattr(
            obj, "__dict__"
        ) else setattr(obj, k, v)

        for member in group:
            setattr(member, "cluster_id", cluster_id)
            setattr(member, "cluster_size", len(group))
            setattr(member, "is_cluster_representative", member is rep)

        stats.representatives += 1
        stats.merged_away += len(group) - 1

    # Sort: representatives first by severity desc, then non-reps grouped.
    representatives = sorted(
        (f for f in findings if getattr(f, "is_cluster_representative", False)),
        key=lambda f: (-_severity_rank(f), getattr(f, "cluster_id", 0)),
    )
    others = sorted(
        (f for f in findings if not getattr(f, "is_cluster_representative", False)),
        key=lambda f: getattr(f, "cluster_id", 0),
    )
    return representatives + others, stats
