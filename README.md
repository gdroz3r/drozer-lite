# drozer-lite

Open-source Claude Code skill for pattern-level smart contract vulnerability scanning.

Supports **Solidity, Rust (Anchor/CosmWasm/IC), Move (Aptos/Sui/Initia), Cairo (StarkNet), and Vyper**.

202 checks across 14 profiles. Runs inside your Claude Code session — no extra API key, no install.

## Install

```bash
git clone https://github.com/gdroz3r/drozer-lite ~/.claude/skills/drozer-lite
```

Restart Claude Code. That's it.

## Usage

```
/drozer-lite path/to/project
```

Or:

```
/drozer-lite path/to/Contract.sol --profile auto
```

| Flag | Purpose |
|---|---|
| `--profile auto` (default) | Auto-detect profiles from keywords |
| `--profile <name>` | Force: `vault`, `lending`, `dex`, `stableswap`, `signature`, `cross-chain`, `governance`, `reentrancy`, `oracle`, `math`, `gaming`, `icp`, `solana` |

## What it does

1. Detects language from file extensions
2. Builds a structural inventory of all in-scope files
3. Auto-detects relevant protocol profiles (DEX, vault, lending, etc.)
4. Clusters files by dependency
5. Applies the checklist against each cluster
6. Runs a cross-cluster sweep for multi-file bugs
7. Outputs deduplicated findings as JSON + Markdown

## Profiles

| Profile | Checks |
|---|---|
| `universal` (always loaded) | 110 |
| `dex` | 11 |
| `vault` | 6 |
| `lending` | 5 |
| `stableswap` | 5 |
| `signature` | 4 |
| `cross-chain` | 13 |
| `governance` | 6 |
| `reentrancy` | 5 |
| `oracle` | 3 |
| `math` | 6 |
| `gaming` | 3 |
| `solana` | 12 |
| `icp` | 16 |

Every check traces to a real audit finding.

## Limits

- Pattern-level only. Does not do multi-step actor reasoning, chain composition, or formal verification.
- Max 1MB source per run. For larger codebases, use `/droz3r`.
- 10-60 min per protocol depending on size.
- Solidity has the deepest coverage. Move/Cairo/Vyper rely on the 110 universal checks with automatic translation.

A clean drozer-lite run is **not** a clean audit.

## License

MIT
