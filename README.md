# drozer-lite

**A pure Claude Code skill for fast, deterministic Solidity vulnerability scanning.**

drozer-lite is a single Claude Code skill that ships a curated checklist of 180 vulnerability patterns across 13 protocol-type profiles. When invoked, it loads the relevant checklist for the target source and reports structured findings — all inside your existing Claude Code session, with no separate API key, no `pip install`, and no extra cost beyond your normal Claude Code usage.

> **Status**: v0.2.0 (skill conversion). Architecture is stable. Checklists are ported from real benchmark gap analysis. The first community validation runs are pending.

## Why drozer-lite

Existing LLM-based Solidity auditors either run a full multi-hour pipeline or rely on hand-crafted rules with no empirical grounding. drozer-lite is different:

- **Empirically curated.** Every check in the bundled checklists originated as a gap-fix after a missed finding in a past benchmark audit (Virtuals, Morph L2, Oku, Superfluid, Perennial V2, Kinetiq, and others). Nothing is speculative.
- **No extra API key.** drozer-lite is a Claude Code skill — it runs inside your existing session and uses the same model you already pay for. There is no separate `ANTHROPIC_API_KEY` requirement.
- **Deterministic methodology.** Every invocation follows the same six-step workflow: identify target → detect profile → load checklists → analyze → output JSON → disclaimer.
- **Developer-shaped.** Default output is canonical JSON that downstream tooling can parse. Markdown variant is one prompt away.
- **Vendor-neutral vocabulary.** Native tags use well-known terms (`reentrancy`, `tx_origin_auth`, `missing_access_control`) with cross-references to SWC Registry and CWE.

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

## How it works

1. **Identify** the target `.sol` file(s) (skips `node_modules`, `lib`, `test`, etc.; refuses inputs over 20KB total).
2. **Detect** the protocol type using a case-insensitive keyword table (threshold = 3 distinct matches per profile). `universal` is always loaded.
3. **Load** the relevant checklist files from `checklists/`.
4. **Analyze** every check against the source. Conservative — false positives are worse than misses.
5. **Output** a single JSON object matching the canonical schema. Markdown variant on request.
6. **Disclose** the limitations: drozer-lite is one pass over a checklist. It is NOT a full audit.

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

- **Not a replacement for a full audit.** It catches pattern-level bugs from a curated checklist. It does not do cross-function state tracing, multi-actor model reasoning, or deep protocol-specific logic analysis. For that, use the full [drozer pipeline](https://github.com/gdroz3r/drozer) (`/droz3r`).
- **Not a formal verifier.** It produces heuristic findings based on a curated checklist, not mathematical guarantees.
- **Not a CLI or library.** drozer-lite v0.1.x shipped a `pip install` CLI; v0.2.0 dropped that in favor of being a pure Claude Code skill. If you need a standalone CLI for CI / non-Claude-Code workflows, fork from the v0.1.0 tag.

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
