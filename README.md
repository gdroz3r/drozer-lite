# drozer-lite

**A fast, deterministic Solidity pattern scanner derived from empirical audit gap analysis.**

drozer-lite is a standalone single-shot auditor for Solidity contracts. It loads a curated checklist of vulnerability patterns — each one derived from a real finding missed during past benchmark audits — and runs a single deterministic LLM pass to produce structured findings. It is designed to drop into any workflow (CLI, CI, Claude Code skill) in minutes.

> **Status: v0.1.0 (early alpha).** Architecture, checklists (180 checks across 13 profiles), LLM pipeline, four output adapters, and the bundled fixture corpus are in place. A real-API benchmark snapshot is pending — see [BENCHMARKS.md](BENCHMARKS.md).

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

drozer-lite ships with 13 profiles, each a targeted checklist of empirically derived checks:

| Profile | Trigger patterns | Checks |
|---|---|---|
| `universal` | always loaded | 95 — access control, semantics, staking, approvals, generic DeFi |
| `signature` | `EIP712`, `permit`, `ecrecover`, `isValidSignature` | 4 — signer/account gap, EIP-712 typehash, permit front-run |
| `vault` | `ERC4626`, `totalAssets`, `previewDeposit`, `convertToShares` | 6 — share inflation, lifecycle residue, slippage protection |
| `lending` | `borrow`, `liquidate`, `collateral`, `LTV`, `healthFactor` | 5 — liquidation timing, accumulator drift, batching boundaries |
| `dex` | `swap`, `addLiquidity`, `amountOutMin`, `IUniswapV[23]`, `sqrtPriceX96` | 6 — loop denominator staleness, partial fill refunds, slippage asymmetry |
| `cross-chain` | `lzReceive`, `ccipReceive`, `setPeer`, `wormhole` | 13 — message replay, payload validation, capacity exhaustion |
| `governance` | `propose`, `castVote`, `quorum`, `delegate`, `Governor`, `Timelock` | 6 — vote replay, quorum types, delegation cleanup |
| `reentrancy` | `nonReentrant`, `ReentrancyGuard`, `.call{value:`, `onERC721Received`, ERC777 hooks | 5 — token callback hooks, settlement reentrancy, cross-function callbacks |
| `oracle` | `AggregatorV[23]Interface`, `latestRoundData`, `priceFeed`, `Pyth` | 3 — failure cascading, freshness DoS, measurement asymmetry |
| `math` | `FixedPoint`, `PRBMath`, `mulDiv`, `WAD`, `RAY`, `UFixed*`, `SD/UD` | 6 — multi-step normalization, formula transposition, decimal scaling |
| `gaming` | `VRFConsumerBase`, `VRFCoordinator`, `randomness`, `requestRandomWords` | 3 — VRF callback gas, raffle profitability, lottery economics |
| `icp` | explicit-only (`--profile icp`) | 16 — Internet Computer canister checks (Rust) |
| `solana` | explicit-only (`--profile solana`) | 12 — Solana / Anchor program checks (Rust) |

Detection is deterministic regex-based with a configurable threshold (`profiles.json`). `universal` is always loaded. `icp` and `solana` are never auto-detected — they're for explicit invocation when auditing non-Solidity code with the same checklist format. Pass `--profile <name>` to override auto-detection for any profile.

**Total**: 180 checks across 13 profiles, every check provenance-cited to a real benchmark finding.

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

1. **Hand-crafted fixture corpus** (`tests/fixtures/`) — 11 vulnerable+clean Solidity pairs, one per profile, used as a regression net.
2. **ScaBench curated corpus** (planned) — judged findings from Code4rena, Sherlock, and Cantina.
3. **Forefy autonomous-audit benchmark** (planned) — public benchmark leaderboard.

Run the bundled fixture benchmark locally:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
./scripts/run-real-benchmark.sh -o BENCHMARKS.md
```

See [BENCHMARKS.md](BENCHMARKS.md) for the scoring methodology and the latest snapshot.

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
