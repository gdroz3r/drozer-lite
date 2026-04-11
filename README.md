# drozer-lite

**A fast, deterministic Solidity pattern scanner derived from empirical audit gap analysis.**

drozer-lite is a standalone single-shot auditor for Solidity contracts. It loads a curated checklist of vulnerability patterns — each one derived from a real finding missed during past benchmark audits — and runs a single deterministic LLM pass to produce structured findings. It is designed to drop into any workflow (CLI, CI, Claude Code skill) in minutes.

> **Status: v0.1.0 (early alpha).** The architecture is stable; the checklists are being ported from the main drozer pipeline.

## Why drozer-lite

Existing LLM auditors either run a full multi-hour pipeline or rely on hand-crafted rules with no empirical grounding. drozer-lite is different:

- **Empirically curated.** Every check in the knowledge base originated as a gap-fix after a missed finding in a past benchmark audit (Virtuals, Morph L2, Oku, Superfluid, Perennial V2, and others). Nothing is speculative.
- **Deterministic.** Temperature 0, single LLM call, same input → same output. Reproducible in CI.
- **Fast.** 3–6 minutes per contract. No multi-phase pipeline, no recon, no orchestration.
- **Developer-shaped.** Default output is a human-readable Markdown report. JSON, SARIF, and benchmark-specific adapters are optional.
- **Vendor-neutral.** Native vocabulary uses well-known terms (reentrancy, tx_origin_auth, missing_access_control) with cross-references to SWC Registry and CWE. Benchmark formats are adapter plugins, not hardcoded conventions.

## Install

```bash
pip install drozer-lite
```

Or from source:

```bash
git clone https://github.com/gdroz3r/drozer-lite.git
cd drozer-lite
pip install -e .
```

## Usage

```bash
# Single file, default Markdown output
drozer-lite audit MyContract.sol

# Whole directory
drozer-lite audit src/

# JSON for tooling
drozer-lite audit MyContract.sol --format json > findings.json

# Explicit profile override
drozer-lite audit MyVault.sol --profile vault

# Stdin
cat MyContract.sol | drozer-lite audit -
```

Requires `ANTHROPIC_API_KEY` in the environment.

## How it works

1. **Collect** the .sol files from the given path (filters node_modules, lib, test, mock).
2. **Detect** the protocol type using deterministic regex patterns (vault, signature, lending, dex, cross-chain, governance).
3. **Assemble** a focused checklist from universal + top-detected profile(s). Typically 40–80 checks, ~3–5K tokens.
4. **Prompt** a single Opus agent at temperature 0 with the checklist, the contract source, strict JSON schema, and few-shot pedagogical examples.
5. **Validate** the response against the schema. Retry once on parse failure.
6. **Canonicalize** vocabulary (e.g., "CEI violation" → `reentrancy`).
7. **Dedup** findings by root cause.
8. **Emit** in the requested format (Markdown, JSON, SARIF, or a benchmark adapter).

## Profiles

drozer-lite ships with 7 profiles, each a targeted checklist:

| Profile | Trigger patterns | Checks |
|---|---|---|
| `universal` | always loaded | access control, reentrancy, tx.origin, unchecked returns, zero-address, integer overflow |
| `signature` | `EIP712`, `permit`, `ecrecover`, `isValidSignature` | replay, unsigned fields, nonce griefing, cross-chain replay |
| `vault` | `deposit`, `withdraw`, `shares`, `totalAssets`, `ERC4626` | first depositor, donation attacks, rounding, share inflation |
| `lending` | `borrow`, `liquidate`, `collateral`, `LTV`, `healthFactor` | liquidation bypass, collateral valuation, bad debt |
| `dex` | `swap`, `addLiquidity`, `amountOutMin`, `UniswapV3` | slippage, oracle manipulation, sandwich attacks |
| `cross-chain` | `lzReceive`, `ccipReceive`, `setPeer`, `wormhole` | message replay, trusted remote, sequence ordering |
| `governance` | `propose`, `cast`, `quorum`, `delegate`, `Governor` | vote buying, flash-loan governance, proposal cancellation |

Detection is deterministic regex-based. Users can override with `--profile`.

## Output formats

| Format | Use case | Default |
|---|---|---|
| `markdown` | CLI readers, human review | ✓ |
| `json` | Tooling, downstream pipelines | |
| `sarif` | GitHub code scanning, CI integration | |
| `forefy` | [Forefy benchmark](https://forefy.com/benchmarks) submission | |

New adapters can be contributed as plugins — see `CONTRIBUTING.md`.

## What drozer-lite is NOT

- **Not a replacement for a full audit.** It catches pattern-level bugs from a curated checklist. It does not do cross-function state tracing, actor model reasoning, or deep protocol-specific logic analysis. For that, use the full [drozer pipeline](https://github.com/gdroz3r/drozer).
- **Not a formal verifier.** It produces heuristic findings from an LLM pass, not mathematical guarantees.
- **Not free to run.** Each invocation makes one Anthropic API call. Budget ~$0.40 per contract at Opus pricing.

## Validation

drozer-lite is validated against three corpora:

1. **Hand-crafted fixtures** (`tests/fixtures/`) — correctness on textbook vulnerability patterns
2. **ScaBench curated corpus** — real judged findings from Code4rena, Sherlock, Cantina
3. **Forefy autonomous-audit** — public benchmark leaderboard

See `BENCHMARKS.md` for scores and per-case breakdowns.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The primary contribution paths are:

- **Adding a profile checklist** — drop a new `checklists/<name>.md` file and a detection pattern to `profiles.json`.
- **Adding a vocabulary entry** — edit `drozer_lite/vocab.py`.
- **Adding an output adapter** — implement a new module in `drozer_lite/adapters/`.
- **Adding test fixtures** — contribute vulnerable and clean Solidity examples to `tests/fixtures/`.

## Acknowledgements

drozer-lite is a slice of the [drozer](https://github.com/gdroz3r/drozer) auditing pipeline. The checklists are derived from gap analysis across real benchmark audits including the ScaBench curated dataset.
