# drozer-lite benchmarks

drozer-lite is validated against three corpora:

1. **Bundled fixture corpus** (`tests/fixtures/`) — 11 hand-crafted vulnerable+clean pairs covering each profile. Used as a regression net: every check must catch its fixture without flagging the clean version.
2. **ScaBench curated corpus** (planned) — judged findings from Code4rena, Sherlock, and Cantina contests, derived from the main drozer benchmark suite.
3. **Forefy autonomous-audit benchmark** (planned) — public benchmark leaderboard.

## Bundled fixture corpus (canonical regression set)

The fixture corpus is the gate every release passes. Run it locally with:

```bash
./scripts/run-real-benchmark.sh -o BENCHMARKS.md
```

This runs `drozer-lite audit` against each `vulnerable.sol` / `clean.sol` pair and reports:

- **Vulnerable detection rate** — fraction of vulnerable fixtures where the LLM returned a finding whose canonical `vulnerability_type` matches the expected one and whose `affected_function` contains the expected name.
- **Clean cleanliness rate** — fraction of clean fixtures where NO finding matches the expected canonical type. (Other findings are tolerated as long as they don't claim the same bug.)

### Latest run

> **Status: not yet executed.** v0.1.0 ships the runner and fixtures but does not include a recorded benchmark snapshot. Run the script above against your own API key, then commit the resulting report here.

| Profile | Expected type | Vuln detected | Clean | Notes |
|---------|---------------|---------------|-------|-------|
| _to be filled by the first real run_ |

### Corpus contents

| Profile     | Vulnerability                              | Source pattern                |
|-------------|--------------------------------------------|-------------------------------|
| universal   | Missing access control on owner setter     | classic                       |
| signature   | Replayable EIP-712 claim (no nonce)        | airdrops, voucher claims      |
| vault       | First-depositor share inflation            | ERC4626 / Silo / Yearn        |
| lending     | Borrow without health-factor recheck       | lending markets               |
| dex         | swap() with no slippage protection         | router wrappers               |
| cross-chain | lzReceive without trusted-remote check     | LayerZero OFTs                |
| governance  | castVote uses live balance, not snapshot   | NFT vote replay               |
| reentrancy  | CEI violation in withdraw()                | classic                       |
| oracle      | Chainlink getPrice without staleness check | price consumers               |
| math        | Decimal scaling mismatch (18 vs 6 dec)     | reward accumulators           |
| gaming      | Raffle uses block.timestamp as randomness  | weak-RNG lottery              |

## ScaBench corpus (planned)

The main drozer pipeline maintains a ground-truth comparison suite from real Code4rena, Sherlock, and Cantina contests. drozer-lite will be scored against the same suite once Phase 6 of the build is locked in.

## Forefy autonomous-audit benchmark (planned)

The `forefy` output adapter is provisional — see the docstring in `drozer_lite/adapters/forefy.py`. The exact submission schema will be validated and the adapter fixed during the first Forefy benchmark run.

## How to interpret a benchmark run

drozer-lite is **one LLM call per audit on a curated checklist**. It is good at catching pattern-level bugs in small contracts. It is NOT a replacement for:

- multi-phase reasoning (the full drozer pipeline does this — see [main drozer](https://github.com/gdroz3r/drozer))
- cross-function actor modeling
- formal property verification
- cross-contract state tracing across thousands of lines

A 100% bundled-fixture pass rate indicates the engine is wired correctly. Real contest performance will be lower, especially on novel protocol types or large multi-contract codebases. That gap is expected, not a bug — the upgrade path is the full drozer pipeline.
