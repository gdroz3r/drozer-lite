# Lending checklist

Triggered when the source contains borrow, liquidate, collateral, LTV, or healthFactor patterns.

> **Status:** Build Phase 1 placeholder. Content ported in Build Phase 2 from the main drozer lending profile.

Categories (to be expanded):

- Liquidation bypass (health factor calculation gaps, collateral exclusion)
- Collateral valuation (stale oracle, decimals mismatch, circuit-breaker bypass)
- Bad debt socialization (insolvent position not recognized)
- Interest rate manipulation (utilization calculation edge cases)
- Borrow cap / supply cap enforcement
- LTV / liquidation threshold on shared collateral types
