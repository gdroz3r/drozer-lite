---
name: drozer-lite
description: Run a single-shot Solidity vulnerability scan using drozer-lite. Use when the user asks "scan this contract", "audit this Solidity file", "run drozer-lite on X", or wants a fast pattern-level review of a small Solidity codebase.
---

# drozer-lite

You have access to drozer-lite, a fast deterministic Solidity pattern scanner. It runs ONE LLM call against a curated checklist of vulnerability patterns and returns structured findings.

## When to use this skill

Use drozer-lite when ALL of the following hold:
- The target is one or more `.sol` files (or a directory of `.sol` files).
- The user wants a quick pattern-level review, not a full audit.
- The total source size is under ~20KB (a single contract or small module — not a 50-file protocol).

Do NOT use drozer-lite for:
- Multi-phase reasoning, cross-function actor modeling, or chain analysis. Use the full drozer pipeline (`/droz3r`) for that.
- Non-Solidity code, unless the user explicitly passes `--profile icp` (Internet Computer / Rust) or `--profile solana` (Anchor / Rust).
- Codebases over 20KB total. drozer-lite refuses by design — point the user at `/droz3r` instead.

## How to invoke

drozer-lite is a Python CLI installed via `pip install drozer-lite`. Check it's available:

```bash
which drozer-lite
```

If not present, instruct the user to install it (`pip install drozer-lite`) before continuing.

Required environment variable: `ANTHROPIC_API_KEY`. If unset, prompt the user to export it.

### Standard invocation

```bash
drozer-lite audit <path-to-sol-or-dir>
```

Optional flags:

| Flag | Purpose |
|---|---|
| `--format markdown` (default) | Human-readable Markdown report |
| `--format json` | Native JSON for downstream tooling |
| `--format sarif` | SARIF v2.1.0 for GitHub code scanning |
| `--format forefy` | Forefy benchmark submission shape |
| `--profile auto` (default) | Deterministic regex detection |
| `--profile <name>` | Force a profile: vault, lending, dex, signature, cross-chain, governance, reentrancy, oracle, math, gaming, icp, solana |
| `--model claude-opus-4-5` | Override the model (default is Opus) |
| `--max-bytes 20000` | Refuse inputs above this size |
| `-o report.md` | Write to file instead of stdout |

### Listing profiles or vocabulary

```bash
drozer-lite list-profiles
drozer-lite list-vocabulary
```

## What you should do with the result

1. Read drozer-lite's output verbatim. Do not paraphrase findings or invent new ones.
2. If the user asked "is this safe?" — summarize the severity counts and call out any CRITICAL/HIGH findings by name.
3. If the user asked for fixes — quote the affected function and offer a remediation drawn from the explanation field. Do not fabricate fix suggestions; the explanation already describes the bug.
4. If `findings` is empty — say so explicitly. drozer-lite caught nothing pattern-level. That does not mean the contract is bug-free, only that no checklist pattern matched.
5. Cluster metadata (`cluster_id`, `is_cluster_representative`) is on each finding when dedup ran. If the user wants a deduplicated view, filter to `is_cluster_representative == true`.

## Honest framing

drozer-lite is one LLM call against a checklist derived from real benchmark gap analysis. It is good at:

- Single-contract pattern bugs (reentrancy, missing access control, slippage, signature replay, oracle staleness, etc.)
- Quick second-opinion review during development

It is bad at:

- Cross-function state tracing across many contracts
- Novel vulnerabilities not covered by any check in the checklist
- Anything requiring multi-step reasoning or actor modeling

Always tell the user: a clean drozer-lite run is NOT the same as a clean audit. For high-value contracts, recommend the full drozer pipeline (`/droz3r`) or a human auditor on top of drozer-lite.
