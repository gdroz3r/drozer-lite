"""Command-line interface for drozer-lite.

Developer-shaped commands:

    drozer-lite audit PATH                    # default markdown output
    drozer-lite audit PATH --format json      # native JSON
    drozer-lite audit PATH --format sarif     # SARIF for CI
    drozer-lite audit PATH --format forefy    # Forefy benchmark format
    drozer-lite audit PATH --profile vault    # explicit profile override
    drozer-lite audit -                       # read from stdin
    drozer-lite list-profiles                 # show available profiles
    drozer-lite list-vocabulary               # show known vulnerability tags
    drozer-lite --version                     # print version
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from drozer_lite import __version__

AVAILABLE_FORMATS = ("markdown", "json", "sarif", "forefy")
AVAILABLE_PROFILES = (
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
)
EXPLICIT_ONLY_PROFILES = frozenset({"icp", "solana"})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="drozer-lite",
        description=(
            "Fast, deterministic Solidity pattern scanner derived from empirical audit "
            "gap analysis. Runs a single LLM pass over a curated checklist and returns "
            "structured findings."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"drozer-lite {__version__}",
    )

    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    # `audit` subcommand
    audit = sub.add_parser(
        "audit",
        help="Scan a .sol file, directory, or stdin for vulnerability patterns",
    )
    audit.add_argument(
        "path",
        help="Path to .sol file, directory of .sol files, or '-' for stdin",
    )
    audit.add_argument(
        "--format",
        "-f",
        choices=AVAILABLE_FORMATS,
        default="markdown",
        help="Output format (default: markdown)",
    )
    audit.add_argument(
        "--profile",
        "-p",
        choices=[*AVAILABLE_PROFILES, "auto"],
        default="auto",
        help="Profile to apply (default: auto-detect based on source)",
    )
    audit.add_argument(
        "--model",
        default="claude-opus-4-6",
        help="Anthropic model to use (default: claude-opus-4-6)",
    )
    audit.add_argument(
        "--max-bytes",
        type=int,
        default=20_000,
        help="Refuse inputs larger than this many bytes (default: 20000)",
    )
    audit.add_argument(
        "--output",
        "-o",
        help="Write output to file instead of stdout",
    )

    # `list-profiles`
    sub.add_parser(
        "list-profiles",
        help="Print the available profile checklists",
    )

    # `list-vocabulary`
    sub.add_parser(
        "list-vocabulary",
        help="Print the known vulnerability type vocabulary",
    )

    # `benchmark`
    bench = sub.add_parser(
        "benchmark",
        help=(
            "Run drozer-lite against the bundled fixture corpus and report "
            "vulnerable-detection / clean-cleanliness rates. Costs ~22 "
            "Anthropic API calls per run."
        ),
    )
    bench.add_argument(
        "--model",
        default="claude-opus-4-5",
        help="Anthropic model identifier (default: claude-opus-4-5)",
    )
    bench.add_argument(
        "--output",
        "-o",
        help="Write the benchmark report to a file instead of stdout",
    )

    return parser


def cmd_audit(args: argparse.Namespace) -> int:
    """Run the audit subcommand."""
    from drozer_lite import audit
    from drozer_lite.adapters import emit, available_formats

    # Validate the path exists early so users get clean errors.
    if args.path != "-" and not Path(args.path).exists():
        print(f"[drozer-lite] ERROR: path not found: {args.path}", file=sys.stderr)
        return 2

    profile_arg = None if args.profile == "auto" else args.profile

    if args.path == "-":
        source = sys.stdin.read()
        result = audit.audit_source(
            [("stdin.sol", source)],
            profile=profile_arg,
            model=args.model,
        )
    else:
        result = audit.audit_path(
            args.path,
            profile=profile_arg,
            model=args.model,
            max_bytes=args.max_bytes,
        )

    if args.format not in available_formats():
        print(
            f"[drozer-lite] ERROR: unknown format {args.format!r}. "
            f"Available: {', '.join(available_formats())}",
            file=sys.stderr,
        )
        return 2

    rendered = emit(result, args.format)

    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered)

    return 0 if not result.warnings or result.findings else 0


def cmd_list_profiles(args: argparse.Namespace) -> int:  # noqa: ARG001
    print("Available profiles:")
    for p in AVAILABLE_PROFILES:
        if p == "universal":
            marker = "  (always loaded)"
        elif p in EXPLICIT_ONLY_PROFILES:
            marker = "  (explicit-only — pass --profile to load)"
        else:
            marker = ""
        print(f"  {p}{marker}")
    print(
        "\nRun 'drozer-lite audit <path>' for automatic detection, "
        "or pass '--profile <name>' to force one."
    )
    return 0


def cmd_list_vocabulary(args: argparse.Namespace) -> int:  # noqa: ARG001
    from drozer_lite.vocab import VOCABULARY

    print(f"drozer-lite native vocabulary ({len(VOCABULARY)} tags):\n")
    for tag, entry in sorted(VOCABULARY.items()):
        refs = []
        if entry.swc_id:
            refs.append(entry.swc_id)
        if entry.cwe_id:
            refs.append(entry.cwe_id)
        ref_str = f" [{', '.join(refs)}]" if refs else ""
        print(f"  {tag}{ref_str}")
        print(f"      {entry.description}")
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    from drozer_lite.benchmark import format_report, run_benchmark

    print("[drozer-lite] running benchmark — this will make Anthropic API calls.", file=sys.stderr)
    print(f"  model: {args.model}", file=sys.stderr)
    report = run_benchmark(model=args.model)
    rendered = format_report(report)

    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
        print(f"[drozer-lite] wrote benchmark report to {args.output}", file=sys.stderr)
    else:
        print(rendered)

    # Non-zero exit if anything missed.
    if report.vulnerable_passed < report.total or report.clean_clean < report.total:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "audit": cmd_audit,
        "list-profiles": cmd_list_profiles,
        "list-vocabulary": cmd_list_vocabulary,
        "benchmark": cmd_benchmark,
    }
    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
