# Lending Checklist

> Profile: lending
> Checks: 5
> Source: ported from Drozer-v2 lending-invariants.md (provenance cited per check)

## Methodology

Lending protocols hold collateral against debt at a time-varying exchange rate driven by oracles. Attackers manipulate price or interest accounting to either withdraw more than they deposited or force wrongful liquidation of healthy positions. For each borrow/repay/liquidate path, trace: (a) which oracle is read, (b) whether staleness and decimal conversions are correct, (c) whether health-factor checks bracket every collateral-moving path, and (d) whether rounding in interest accrual and liquidation math favors the protocol. Test boundary states explicitly: fresh market, frozen asset, paused underlying, extreme utilization, and dust positions.

## Checks

### LEND-1: Collateralization / Health Factor Bracket
**Provenance**: lending-invariants.md L1
**Pattern**: A collateral-withdrawal, borrow, or collateral-swap path mutates position state without re-checking the health factor afterwards, allowing undercollateralized exits.
**Methodology**: Enumerate every path that reduces collateral OR increases debt. For each, verify a health-factor check occurs AFTER the state mutation (not before). Check that collateral valuation uses current oracle prices with proper decimal handling and the LTV limit for the specific asset.
**Red flags**:
- `withdraw(amount); updatePosition(); // no HF check`
- Borrow path that checks HF against stale cached price
- Collateral swap (oldAsset→newAsset) with HF computed only on old asset

### LEND-2: Interest Accrual Monotonicity & Precision
**Provenance**: lending-invariants.md L2
**Pattern**: Interest index resets, decreases, or loses precision, allowing debt reduction or underflow.
**Methodology**: For each interest-index function, verify the index is strictly non-decreasing under every path. Verify large time gaps do not overflow. Check rounding direction: debt rounds up, supply rounds down.
**Red flags**:
- Interest index reset on pause/unpause
- `accrueInterest()` not called before health-factor read
- Compound math using `divide-before-multiply`

### LEND-3: Liquidation Fairness & Bad Debt Prevention
**Provenance**: lending-invariants.md L3 + L5
**Pattern**: Liquidations fire on healthy positions due to stale oracle prices, or liquidators leave unprofitable dust positions behind that accumulate into bad debt.
**Methodology**: Verify oracle freshness is checked at liquidation time. Verify the liquidation bonus does not push the position into bad debt (bonus must not exceed remaining margin). Verify close-factor limits. Test dust positions: can a liquidator profitably close them? If not, a shortfall / bad-debt socialization mechanism must exist.
**Red flags**:
- `latestRoundData()` used without staleness threshold
- Liquidation penalty > remaining collateral
- No dust-close mechanism for positions below gas cost

### LEND-4: Oracle Integration (Staleness, Decimals, Failure Modes)
**Provenance**: lending-invariants.md L7
**Pattern**: Oracle reads omit staleness, don't handle Chainlink decimals correctly, or lack a fallback for zero/reverting feeds.
**Methodology**: For every oracle read, verify (a) `updatedAt` staleness check against asset-specific heartbeat, (b) decimal conversion between feed and internal math, (c) handling of `price <= 0` and reverts, and (d) at least one fallback source for high-value operations.
**Red flags**:
- `getPrice()` ignores `updatedAt`
- Assumes 18-decimal feed for an 8-decimal Chainlink aggregator
- No circuit breaker on extreme deviations

### LEND-5: Flash-Loan + Price Manipulation on Borrow
**Provenance**: lending-invariants.md L9 + L7
**Pattern**: An attacker flash-loans tokens, manipulates a spot price used for collateral valuation, borrows against the inflated collateral, then repays the flash loan with the borrowed funds.
**Methodology**: For every collateral that can be valued against a manipulable source (Uniswap spot reserves, `balanceOf`, in-protocol AMM), verify the price is derived from TWAP or external oracle. Check whether the same block can host both manipulation and borrow.
**Red flags**:
- Collateral price derived from `pool.getReserves()` directly
- TWAP window < 1 block effective
- No reentrancy guard on borrow path used during a flash-loan callback
