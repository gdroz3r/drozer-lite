# drozer-lite examples

A small fixture corpus of vulnerable + clean Solidity pairs covering each profile drozer-lite ships with. Each pair demonstrates one canonical pattern from the bundled checklist and the clean version shows the intended remediation.

These files exist to help you smoke-test the skill. After installing drozer-lite into Claude Code, point it at one of the vulnerable files:

```
/drozer-lite examples/fixtures/reentrancy/vulnerable.sol
```

Or from natural language:

```
audit examples/fixtures/vault/vulnerable.sol with drozer-lite
```

The skill should detect the vulnerability and report it. The clean variant should NOT trigger the same finding.

## Corpus contents

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

`expectations.json` pins each fixture's profile, expected canonical `vulnerability_type`, and expected `affected_function`. Use it as ground truth if you want to compare a real run against what the skill should produce.

## What this corpus is NOT

These fixtures are pedagogical, not adversarial. A 100% pass rate proves the skill is wired correctly — it does NOT predict performance on real Code4rena or Sherlock contests. For that, run the skill against contest snapshots and compare against the published findings list.
