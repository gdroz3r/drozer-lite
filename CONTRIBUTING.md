# Contributing to drozer-lite

Thanks for considering a contribution. drozer-lite is designed to be easy to extend along four axes: **profiles**, **vocabulary**, **adapters**, and **fixtures**. This doc walks through each.

## Project philosophy

drozer-lite is intentionally narrow:

- **One LLM call per audit.** Multi-agent orchestration belongs in the main [drozer](https://github.com/gdroz3r/drozer) pipeline.
- **Deterministic.** Temperature 0, reproducible output, same input → same finding set.
- **Developer-shaped.** Output is Markdown by default. JSON and benchmark formats are opt-in.
- **Empirically curated.** Every check in a checklist should trace to a real audit finding that was missed before. No speculative patterns.

Contributions that preserve these properties are welcome. Contributions that add orchestration, multi-agent flows, or benchmark-specific tuning to the core path will be redirected to the main drozer pipeline or rejected.

## Adding a profile checklist

1. Create `checklists/<your-profile>.md` with one `### <CHECK-N>: <Title>` section per pattern. Use the format already in place: **Provenance**, **Pattern**, **Methodology**, **Red flags**.
2. Each check must trace to a real audit finding — cite the source in the **Provenance** line.
3. Add the profile's detection regex patterns to `profiles.json` under `profiles.<your-profile>.patterns`. Detection is case-insensitive — pick keywords that appear at least 3 times in real code that uses this protocol type. Add the profile to either `always_loaded` or `explicit_only` if it should bypass auto-detection.
4. Add the profile name to `cli.AVAILABLE_PROFILES` in `drozer_lite/cli.py`.
5. Add a vulnerable and clean test fixture to `tests/fixtures/<your-profile>/{vulnerable,clean}.sol` and an entry in `tests/fixtures/expectations.json`.
6. Run `pytest`.
7. Open a PR with: rationale, source benchmark project the checks came from, fixture rationale.

## Adding a vocabulary entry

Edit `drozer_lite/vocab.py` and add a new `VocabEntry` to the `VOCABULARY` dict. Required fields: `tag`, `description`. Recommended: `swc_id`, `cwe_id`.

## Adding an output adapter

1. Create `drozer_lite/adapters/<your-format>.py` with a single `format_<name>(result: AuditResult) -> str` function.
2. Register it in `_bootstrap_default_adapters()` in `drozer_lite/adapters/__init__.py`.
3. Add `<your-format>` to `AVAILABLE_FORMATS` in `drozer_lite/cli.py`.
4. Add a round-trip test in `tests/test_adapters.py`.

## Adding test fixtures

`tests/fixtures/` holds small hand-crafted .sol files that serve as ground truth for the audit engine. Each fixture pairs a vulnerable version with a clean version so we can test both recall (finding real bugs) and precision (not flagging clean code).

Fixtures are the primary regression net. If you find a bug in drozer-lite where it misses an obvious pattern, add a fixture for it first, then fix the code.

## Development setup

```bash
git clone https://github.com/gdroz3r/drozer-lite.git
cd drozer-lite
pip install -e ".[dev]"
pytest
```

Run the CLI:

```bash
drozer-lite --help
drozer-lite list-profiles
drozer-lite list-vocabulary
drozer-lite audit tests/fixtures/reentrancy/vulnerable.sol
```

Run the benchmark suite (costs real money — needs `ANTHROPIC_API_KEY`):

```bash
./scripts/run-real-benchmark.sh -o BENCHMARKS.md
```

## Commit and PR conventions

- Commits should be focused — one logical change per commit.
- PRs should describe: **what** changed, **why** it matters, and **how** it was tested.
- Reference the benchmark project or real finding that motivated the change.
- No benchmark-specific optimizations in core. Benchmark adapters live in `drozer_lite/adapters/`.
