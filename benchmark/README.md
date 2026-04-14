# drozer-lite benchmark harness

Vendor-neutral regression harness for drozer-lite. Runs the skill against any benchmark that provides (a) per-case source folders and (b) an expected answer key, and scores the result.

## Currently supported benchmarks

- **Forefy autonomous-audit** — https://github.com/forefy/benchmarks

Support for additional benchmarks only requires adding a small adapter in `adapters/` that maps the benchmark's layout + schema into the generic harness interface.

## Purpose

Regression gate for methodology changes. Every change to `SKILL.md` or the checklists under `checklists/` must not regress the overall score on any supported benchmark.

The baseline for the Forefy autonomous-audit public corpus as of v0.5.0 is recorded in `baseline.json`.

## Running

```
./benchmark/run.sh forefy-autonomous-audit
```

The script:
1. Clones (or updates) the benchmark repo at a pinned commit
2. Sparse-checks out the public corpus + program.md + scorer.py + expected.json
3. Runs drozer-lite on each case (via Claude Code subagents; each case is independent)
4. Collects per-case findings into the benchmark's required `output.json` schema
5. Invokes the benchmark's own scorer to compute a float 0.0–1.0
6. Diffs the result against `baseline.json` and reports per-case deltas

## Principles

- **No benchmark-specific hardcoding in drozer-lite.** The harness adapts benchmark schemas to the skill; the skill itself never changes based on "which benchmark is running."
- **Regressions block.** A methodology change that improves overall score but regresses any individual case needs to be re-examined — drozer-lite should not get better at benchmarks by breaking other benchmarks.
- **Reproducibility.** Benchmark repos are pinned to a specific commit hash in `adapters/*.yaml`.
