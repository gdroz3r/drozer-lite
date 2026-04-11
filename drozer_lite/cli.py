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
)


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

    return parser


def cmd_audit(args: argparse.Namespace) -> int:
    """Run the audit subcommand."""
    # Build Phase 1 scaffold: the real implementation lands in Build Phase 3.
    # For now, just validate arguments and print what WOULD happen.
    print(f"[drozer-lite v{__version__}] audit command received", file=sys.stderr)
    print(f"  path:    {args.path}", file=sys.stderr)
    print(f"  format:  {args.format}", file=sys.stderr)
    print(f"  profile: {args.profile}", file=sys.stderr)
    print(f"  model:   {args.model}", file=sys.stderr)
    print("", file=sys.stderr)
    print(
        "[drozer-lite] Build Phase 1 scaffold — audit pipeline not yet wired. "
        "This will call drozer_lite.audit.audit_path() in Build Phase 3.",
        file=sys.stderr,
    )

    # Validate the path exists so users get early feedback even in scaffold mode.
    if args.path != "-" and not Path(args.path).exists():
        print(f"[drozer-lite] ERROR: path not found: {args.path}", file=sys.stderr)
        return 2
    return 0


def cmd_list_profiles(args: argparse.Namespace) -> int:  # noqa: ARG001
    print("Available profiles:")
    for p in AVAILABLE_PROFILES:
        marker = "  (always loaded)" if p == "universal" else ""
        print(f"  {p}{marker}")
    print(
        "\nRun 'drozer-lite audit <path>' for automatic detection, "
        "or pass '--profile <name>' to force one."
    )
    return 0


def cmd_list_vocabulary(args: argparse.Namespace) -> int:  # noqa: ARG001
    # Build Phase 1 scaffold: the real list comes from drozer_lite.vocab in Build Phase 4.
    print(
        "[drozer-lite] Build Phase 1 scaffold — vocabulary list lands in Build Phase 4. "
        "See drozer_lite/vocab.py when populated."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "audit": cmd_audit,
        "list-profiles": cmd_list_profiles,
        "list-vocabulary": cmd_list_vocabulary,
    }
    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
