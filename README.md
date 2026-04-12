# drozer-lite

**An open-source Claude Code skill for pattern-level smart contract vulnerability scanning — Solidity, Rust, Move, Cairo, Vyper.**

drozer-lite is a single Claude Code skill that ships a curated checklist of 180+ vulnerability patterns across 13+ protocol-type profiles. When invoked, it detects the target language, walks any smart contract project (single file or multi-file), builds an inventory, clusters related modules, applies the relevant checklist with language-aware red-flag translation, and reports structured findings with cross-file awareness — all inside your existing Claude Code session, with no separate API key, no `pip install`, no extra cost beyond your normal Claude Code usage.

> **Status**: v0.4.0 (multi-language). Audits real multi-file protocols up to 1MB / ~100 files across Solidity, Rust (Anchor/CosmWasm/IC), Move (Aptos/Sui/Initia), Cairo (StarkNet), and Vyper. 10-30 min per protocol, zero marginal cost inside Claude Code.

## Why drozer-lite

Existing LLM-based Solidity auditors either run a full multi-hour pipeline (expensive, slow, closed-source) or rely on hand-crafted rules with no empirical grounding (noisy, incomplete). drozer-lite is different:

- **Empirically curated.** Every check in the bundled checklists originated as a gap-fix after a missed finding in a past benchmark audit. Nothing is speculative.
- **Multi-language.** Solidity, Rust (Anchor, CosmWasm, IC canisters), Move (Aptos, Sui, Initia), Cairo (StarkNet), Vyper. ~88 checks are language-agnostic patterns; ~10 are EVM-specific. The LLM translates Solidity-phrased red flags to the target language's equivalent automatically.
- **Works on real protocols.** Multi-file aware. Clusters related contracts/modules and runs a cross-cluster sweep for bugs that span files. Up to 1MB / ~100 files per run.
- **No extra API key.** drozer-lite is a Claude Code skill — it runs inside your existing session. Zero marginal cost.
- **Deterministic methodology.** Every invocation follows the same 8-step workflow: identify + detect language → inventory → detect profile → cluster → per-cluster analysis → cross-cluster sweep → dedup → honest framing.
- **Developer-shaped.** Default output is canonical JSON. Markdown variant on request.
- **Vendor-neutral vocabulary.** Native tags use well-known terms (`reentrancy`, `missing_access_control`, `missing_signer_check`, `arbitrary_cpi`) with cross-references to SWC Registry and CWE where applicable.

## Install

drozer-lite is a Claude Code skill. To install it, clone the repo into your Claude Code skills directory:

```bash
git clone https://github.com/gdroz3r/drozer-lite ~/.claude/skills/drozer-lite
```

Restart Claude Code (or reload skills) so it picks up the new skill.

That's it. No `pip install`, no API key, no Python environment.

## Usage

From inside Claude Code:

```
/drozer-lite path/to/Contract.sol
```

Or via natural language — the skill description triggers on phrases like "audit this Solidity file", "scan for security bugs", "review this contract":

```
audit examples/fixtures/vault/vulnerable.sol with drozer-lite
```

Optional flags you can mention in your prompt (the skill recognizes them):

| Flag | Purpose |
|---|---|
| `--profile auto` (default) | Deterministic regex detection |
| `--profile <name>` | Force a profile: `vault`, `lending`, `dex`, `signature`, `cross-chain`, `governance`, `reentrancy`, `oracle`, `math`, `gaming`, `icp`, `solana` |
| `--format markdown` | Render the result as a Markdown report instead of JSON |

## How it works (8-step workflow)

1. **Identify the target + detect language** — walk source files by extension (`.sol`, `.rs`, `.move`, `.cairo`, `.vy`); auto-detect language; soft warn at 500KB, hard refuse at 1MB.
2. **Build inventory** — structural extraction for every file (modules, functions, state, guards, external calls, imports). Cheap, ~30 sec per file. Language-aware concept mapping.
3. **Detect profiles** — case-insensitive keyword table (threshold = 3 distinct matches per profile). `universal` always loaded. Language-specific profiles (`solana`, `icp`) auto-load when Rust framework keywords detected.
4. **Cluster the codebase** — group related contracts by inheritance, imports, and directory into 30-50KB clusters.
5. **Per-cluster analysis** — apply each loaded check against each cluster's full source. Conservative: false positives are worse than misses.
6. **Cross-cluster sweep** — detect bugs that span clusters (auto-route fallbacks, cross-contract ACL gaps, staleness mismatches). This is the v0.3.0 difference.
7. **Dedup + output** — structural dedup, canonical JSON (or Markdown variant on request).
8. **Honest framing** — mandatory disclaimer: drozer-lite is pattern-level only, NOT a full audit.

## Time expectations

| Protocol size | Files | Clusters | Wall-clock |
|---|---|---|---|
| Single contract (≤30KB) | 1 | 1 | 5-10 min |
| Small protocol (≤100KB) | 2-10 | 2-3 | **20-35 min** |
| Medium protocol (≤300KB) | 10-30 | 4-8 | **40-60 min** |
| Large protocol (≤500KB) | 30-60 | 8-15 | **60-90 min** |
| Very large (>500KB) | 60+ | 15+ | **90-150 min** (soft warn) |
| >1MB | — | — | **refuses** — recommends `/droz3r` |

Time numbers updated in v0.3.1 after the first real-protocol validation run on Kinetiq (100KB, 3 clusters, ~30 min wall-clock). The earlier v0.3.0 estimates were optimistic — doing the workflow rigorously (inventory + cluster + per-cluster analysis + cross-cluster sweep + dedup) is closer to 30 min for a small protocol than 15.

Zero marginal cost inside Claude Code. drozer-lite is a **coffee-break tool**, not an instant tool. That trade is what makes it useful for real protocols instead of pedagogical toys.

## What drozer-lite catches (and what it doesn't)

**Structural product boundary.** drozer-lite is pattern-level. On Kinetiq (25 ground-truth findings), v0.3.0 hit **40% exact / 56% inclusive**, comparable to the full drozer pipeline on inclusive rate and **beating it on Medium and Low tiers**. But drozer-lite hit **0/3 Highs exactly** (1/3 partial).

This is not a bug, it's the boundary:

| Bug class | drozer-lite catches? | Why |
|---|---|---|
| Reentrancy, CEI violations | ✅ | Single-function pattern |
| Missing access control | ✅ | Single-function pattern |
| Missing slippage / staleness / pause | ✅ | Single-function pattern |
| Unbounded loops / array growth | ✅ | Structural pattern |
| Decimal scaling mismatch | ✅ | Arithmetic pattern |
| Storage collision / uninit proxy | ✅ | Layout pattern |
| **Multi-step economic logic** (e.g. buffer accumulation over time) | ❌ | Needs actor modeling |
| **Temporal ordering unfairness** (e.g. queue before/after slash) | ❌ | Needs event sequence reasoning |
| **Cross-function state invariants** across 5+ calls | ❌ | Needs multi-step tracing |
| **Chain-of-bugs composition** (bug A enables bug B) | ❌ | Needs `/droz3r` chain analysis |

If your protocol's highest-severity bugs are multi-step economic logic, **drozer-lite will not find them**. Use `/droz3r` or a human auditor for those. drozer-lite is the fast, reliable pattern-level second opinion — not the full audit.

## Profiles

drozer-lite ships with 13 profiles, each a targeted checklist of empirically derived checks:

| Profile | Trigger keywords | Checks |
|---|---|---|
| `universal` | always loaded | 95 — access control, semantics, staking, approvals, generic DeFi |
| `signature` | `EIP712`, `permit`, `ecrecover`, `isValidSignature` | 4 — signer/account gap, EIP-712 typehash, permit front-run |
| `vault` | `ERC4626`, `totalAssets`, `previewDeposit`, `convertToShares` | 6 — share inflation, lifecycle residue, slippage protection |
| `lending` | `borrow`, `liquidate`, `collateral`, `LTV`, `healthFactor` | 5 — liquidation timing, accumulator drift, batching boundaries |
| `dex` | `swap`, `addLiquidity`, `amountOutMin`, `IUniswapV2/3` | 6 — loop denominator staleness, partial fill refunds, slippage asymmetry |
| `cross-chain` | `lzReceive`, `ccipReceive`, `setPeer`, `wormhole` | 13 — message replay, payload validation, capacity exhaustion |
| `governance` | `propose`, `castVote`, `quorum`, `delegate`, `Governor` | 6 — vote replay, quorum types, delegation cleanup |
| `reentrancy` | `nonReentrant`, `ReentrancyGuard`, `.call{value:`, ERC777 hooks | 5 — token callback hooks, settlement reentrancy, cross-function callbacks |
| `oracle` | `AggregatorV3Interface`, `latestRoundData`, `priceFeed`, `Pyth` | 3 — failure cascading, freshness DoS, measurement asymmetry |
| `math` | `FixedPoint`, `PRBMath`, `mulDiv`, `WAD`, `RAY`, `UFixed*` | 6 — multi-step normalization, formula transposition, decimal scaling |
| `gaming` | `VRFConsumerBase`, `VRFCoordinator`, `randomness`, `requestRandomWords` | 3 — VRF callback gas, raffle profitability, lottery economics |
| `icp` | explicit-only (`--profile icp`) | 16 — Internet Computer canister checks (Rust) |
| `solana` | explicit-only (`--profile solana`) | 12 — Solana / Anchor program checks (Rust) |

Detection is case-insensitive. `universal` is always loaded. `icp` and `solana` are never auto-detected — they're for explicit invocation when auditing non-Solidity code with the same checklist format.

**Total**: 180 checks across 13 profiles, every check provenance-cited to a real benchmark finding.

## What drozer-lite is NOT

- **Not a replacement for a full audit.** It catches pattern-level bugs from a curated checklist with cross-file awareness. It does NOT do multi-step actor reasoning, chain-composition analysis, or formal verification. For that, use the full [drozer pipeline](https://github.com/gdroz3r/drozer) (`/droz3r`) or a human auditor.
- **Not a formal verifier.** Heuristic findings from a curated checklist, not mathematical guarantees.
- **Not a CLI or library.** Pure Claude Code skill since v0.2.0. Fork from the v0.1.0 tag if you need a standalone CLI.
- **Not instant.** A real multi-file protocol run is 10-30 min. That's the cost of cross-file awareness.
- **Not equally deep in every language.** Solidity has the deepest checklist coverage (98 universal + 6 profiles). Rust/Anchor and IC have dedicated profiles (12 + 16 checks). Move, Cairo, and Vyper rely on the 88 language-agnostic universal checks with automatic red-flag translation. Coverage depth will grow as benchmarks against non-Solidity protocols are run.

## Validation

drozer-lite ships with a small fixture corpus in `examples/fixtures/` — 11 vulnerable+clean Solidity pairs covering each profile. Use them to smoke-test the skill after install:

```
/drozer-lite examples/fixtures/reentrancy/vulnerable.sol
```

The skill should detect a `reentrancy` finding on `withdraw`. The clean variant should NOT trigger the same finding. See `examples/README.md` for the full corpus map and `examples/fixtures/expectations.json` for ground truth.

For a published validation against real Code4rena / Sherlock contests, see the main [drozer pipeline](https://github.com/gdroz3r/drozer) — drozer-lite is the pattern-level slice of that pipeline and inherits its empirical grounding through the ported checklists.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The primary contribution paths are:

- **Adding a profile checklist** — drop a new `checklists/<name>.md` file in the canonical Provenance / Pattern / Methodology / Red flags format and add detection keywords to the table in `SKILL.md`.
- **Adding test fixtures** — drop vulnerable + clean Solidity pairs into `examples/fixtures/<profile>/` and pin them in `examples/fixtures/expectations.json`.
- **Adding a vocabulary tag** — append a new entry to the canonical vocabulary section in `SKILL.md`.

## Acknowledgements

drozer-lite is the open-source pattern-level slice of the [drozer](https://github.com/gdroz3r/drozer) auditing pipeline. The checklists are derived from gap analysis across real benchmark audits including the ScaBench curated dataset.
