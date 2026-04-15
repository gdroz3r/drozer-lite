# Oracle Checklist

> Profile: oracle
> Checks: 3
> Source: ported from Drozer-v2 invariant-templates.md OR1-5 + lending-invariants.md L7 (provenance cited per check)

## Methodology

Any contract that reads an external price feed inherits all of that feed's failure modes: staleness, deviation, zero/negative prices, circuit-breaker halts, decimal mismatch, and outright reverts. Attackers manipulate prices via flash loans (spot reserves) or wait out heartbeats (Chainlink). Every oracle consumer must (a) validate freshness against the feed's asset-specific heartbeat, (b) convert decimals to the contract's internal math, (c) handle `price <= 0` and feed reverts, and (d) degrade gracefully rather than brick permanently. If multiple functions read the same feed, they must all use the same staleness threshold and fallback.

## Checks

### ORACLE-1: Staleness Protection (Per-Asset Heartbeat)
**Provenance**: invariant-templates.md OR-1 + lending-invariants.md L7
**Pattern**: Oracle price reads omit a staleness check or use a one-size-fits-all threshold that is too loose for volatile assets and too tight for stable ones.
**Methodology**: For every oracle read, verify `require(updatedAt >= block.timestamp - heartbeat)` where `heartbeat` is the asset-specific value (Chainlink publishes per-feed heartbeats). Verify the same heartbeat is used by every reader of the same feed (see ORACLE-3). Verify `updatedAt != 0` to reject uninitialized feeds.
**Red flags**:
- `(, int256 price, , , ) = feed.latestRoundData()` with no `updatedAt` usage
- Single `MAX_STALENESS` constant applied to a mix of ETH (20m) and stablecoin (24h) feeds
- No lower bound on `updatedAt`

### ORACLE-2: Manipulation Resistance & Graceful Degradation
**Provenance**: invariant-templates.md OR-2 + OR-3 + OR-4
**Pattern**: A price used for liquidation, borrowing, or minting is derived from instantaneous on-chain state (spot reserves, `balanceOf`) and can be flash-loan-manipulated in a single block; or a single oracle failure bricks the protocol; or a stale/zero feed is silently accepted.
**Methodology**: For every security-critical price, verify the source is TWAP, Chainlink, or another time-weighted mechanism. Verify the protocol pauses (not reverts permanently) on oracle failure. For high-value operations, verify prices are cross-checked against a second source OR bounded by a circuit breaker.
**Red flags**:
- `getPrice() = reserve1 * 1e18 / reserve0` for a liquidation decision
- Hard revert with no admin pause path if the feed returns zero
- Single-source pricing for >$10M positions
- `price <= 0` not explicitly handled

### ORACLE-3: Feed Consistency Across Readers (Decimal & Threshold Uniformity)
**Provenance**: invariant-templates.md OR-5 + lending-invariants.md L7
**Pattern**: Multiple functions read the same oracle feed but apply different staleness thresholds, different decimal conversions, or different fallbacks, producing inconsistent behavior (one function accepts a price another rejects).
**Methodology**: For each oracle feed, identify every reader. Build a reader matrix: [function, staleness threshold, decimal conversion, fallback]. Verify all rows are identical (or the differences are explicitly justified). Verify decimal conversion matches the feed (Chainlink returns 8 or 18 depending on the feed; do not assume 18).
**Red flags**:
- `getPrice()` uses 1h staleness but `liquidate()` reads the same feed with 24h
- `getPrice()` converts from 8 decimals while `isSolvent()` assumes 18
- One function falls back to secondary, another reverts
