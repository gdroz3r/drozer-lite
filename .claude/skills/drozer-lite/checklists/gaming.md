# Gaming / Outcome Determinism Checklist

> Profile: gaming
> Checks: 3
> Source: ported from Drozer-v2 injectable skill OUTCOME_DETERMINISM + universal-invariants.md U7 (timestamp) (provenance cited per check)

## Methodology

Game-like and lottery-like protocols distribute finite prize pools or make time-gated decisions whose outcomes attackers can observe before committing. The core failure modes are (a) pseudo-randomness derivable from on-chain state, (b) finite-pool selection where the depletion fallback reveals the secret, (c) observable default outcomes on time-gated actions that let attackers simulate before acting, and (d) selective-revert callbacks where the winner can force a re-roll by reverting an unfavorable result. Apply adversarial thinking: assume the attacker can simulate the contract at the block they'll be included in, and ask whether they can force any outcome in their favor.

## Checks

### GAME-1: On-Chain Randomness Predictability
**Provenance**: universal-invariants.md U7 + general Solidity RNG failure modes
**Pattern**: "Randomness" is derived from `block.timestamp`, `block.prevrandao`, `blockhash`, or `keccak256` over on-chain state; an attacker simulating the block predicts the outcome and only commits if it favors them.
**Methodology**: For every random-selection path, identify the seed source. Any seed derivable from in-block state is unsafe for value-carrying decisions. Verify commit-reveal with a future block hash, VRF (Chainlink, Pyth Entropy), or cross-transaction entropy. Verify that users cannot observe the seed and cancel.
**Red flags**:
- `uint256 seed = uint256(keccak256(abi.encodePacked(block.timestamp, msg.sender, nonce)))`
- `blockhash(block.number - 1)` used for selection
- Commit-reveal where the reveal can be skipped when unfavorable

### GAME-2: Finite-Pool Selection & Depletion Fallback
**Provenance**: injectable skill OUTCOME_DETERMINISM (finite-pool selection with depletion fallback)
**Pattern**: A finite prize pool selects items with a fallback when the pool is empty; the attacker depletes the pool to force the fallback outcome. Alternatively, the depletion state is observable before action, letting attackers choose when to commit.
**Methodology**: For every finite-pool selection, enumerate the depletion state and the fallback outcome. Ask whether the attacker can (a) observe the depletion state atomically and skip, (b) intentionally deplete the pool to force the fallback, or (c) time their action around another's commitment. Verify the fallback does not provide a profitable alternative.
**Red flags**:
- `if (remainingPrizes == 0) return consolationPrize;` where consolation is valuable enough to target
- Attacker can call `peek()` view functions to check pool state atomically
- Prize pool re-filled mid-round from an attacker-influenced source

### GAME-3: Time-Gated Actions with Observable Default Outcomes / Selective Callback Revert
**Provenance**: injectable skill OUTCOME_DETERMINISM (time-gated actions + callback selective revert; latter is now always-on in depth templates per skill-index)
**Pattern**: A time-gated action has a default outcome if the user does not act within the window; the attacker observes the would-be outcome and acts only if unfavorable (letting the default apply otherwise). Or: a callback (RNG consumer, settlement callback) can selectively revert on unfavorable outcomes, forcing a re-roll.
**Methodology**: For every time-gated mechanism, identify the default outcome and whether attackers can observe the alternative before acting. For every callback that consumes a random result, verify the callback cannot revert on unfavorable outcomes (use try/catch to absorb reverts, or require the callback to be made by the protocol not the user).
**Red flags**:
- `if (block.timestamp > deadline) { applyDefault(); } else { requireUserAction(); }` where the user knows both outcomes
- RNG consumer contract that reverts in `fulfillRandomWords` when result is unfavorable
- Settlement callback callable by the winning party who can choose to revert
