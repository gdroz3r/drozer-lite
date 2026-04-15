# StableSwap Checklist

> Profile: stableswap
> Checks: 5
> Source: drozer-lite v0.4.2 — derived from Curve StableSwap implementation patterns and real-audit findings on StableSwap forks. These checks apply to any protocol implementing the Curve StableSwap invariant (An∑xi + D = ADⁿ + Dⁿ⁺¹/(nⁿ∏xi)).

## Methodology

StableSwap pools maintain a hybrid invariant between constant-sum (x+y=k) and constant-product (xy=k), controlled by an amplification parameter A. Correct implementations must: (a) normalize all token amounts to a common decimal base before computing the invariant D, (b) include ALL pool tokens in the invariant computation (not just the swap pair), (c) charge fees on imbalanced deposits proportional to the skew introduced, (d) handle Newton-Raphson non-convergence as an error rather than returning a wrong result, and (e) allow the amplification parameter to be adjusted over time to respond to market conditions. Compare the implementation against the Curve reference line by line, paying particular attention to how many tokens participate in D/y computation and whether decimal scaling is consistent across swap and LP paths.

## Detection Keywords

Auto-load this profile when **3 or more** of these keywords match (case-insensitive):

`StableSwap`, `amp`, `amplification`, `compute_d`, `compute_y`, `newton`, `invariant.*D`, `stableswap_y`, `n_coins.*ann`, `D_prod`, `amp_factor`

## Checks

### SS-1: Decimal Normalization Inconsistency Between Swap and LP Paths
**Provenance**: drozer-lite v0.4.2 — class-of-bug: the swap path normalizes token amounts to a common decimal base before computing the StableSwap invariant, but the LP minting path uses raw (unnormalized) amounts, producing a different D value and incorrect share calculations for tokens with different decimals.
**Pattern**: A StableSwap implementation has two code paths that compute the invariant D: one for swaps (which normalizes via `decimal_with_precision` or rate multipliers) and one for LP minting/withdrawal (which sums raw amounts). When tokens have different decimals (e.g., 6 vs 18), the LP path computes a D that is dominated by the higher-decimal token, granting disproportionate shares to depositors of that token.
**Methodology**:
1. Identify every call site that computes the StableSwap invariant D.
2. For each call site, check whether token amounts are normalized to a common decimal base BEFORE being passed to the D computation.
3. Compare the normalization logic between the swap path and the LP mint path. If they differ, flag.
4. Test with two tokens of different decimals (e.g., 6 and 18): deposit equal-value amounts via both paths and compare the D values.
**Red flags**:
- Swap path: `offer_pool = Decimal256::decimal_with_precision(amount, precision)` — normalized
- LP path: `sum_x = deposits.iter().fold(zero, |acc, x| acc + x.amount)` — raw amounts, no normalization
- D computation for LP uses raw `Uint128` amounts while swap uses `Decimal256` with precision
- Two tokens with 6 and 18 decimals: depositing 1e6 USDC and 1e18 DAI produces wildly different D vs depositing 1e18 USDC and 1e6 DAI — but both should be equivalent in value

### SS-2: Multi-Token Invariant Uses Only Swap Pair (Disjoint Computation)
**Provenance**: drozer-lite v0.4.2 — class-of-bug: a StableSwap pool with 3+ tokens computes the invariant D and the swap output y using only the offer and ask token balances, ignoring the other pool tokens. The Curve invariant requires ALL token balances to compute D correctly.
**Pattern**: The StableSwap invariant D is defined over ALL N tokens: `An∑(all xi) + D = ADⁿ + Dⁿ⁺¹/(nⁿ∏(all xi))`. When computing a swap between token A and token B in a 3-token pool, the implementation passes only `(offer_pool, ask_pool)` to the D/y computation, but uses `n_coins = 3`. This produces an incorrect D because the sum and product only include 2 of the 3 token balances, while the exponent uses N=3. Swaps between different pairs in the same pool preserve different (incorrect) invariants, creating arbitrage opportunities.
**Methodology**:
1. For every StableSwap swap computation, check how many token balances are passed to the D/y computation function.
2. If the function receives only the offer and ask balances (2 tokens) but `n_coins` reflects the actual pool size (3+), flag as HIGH.
3. Compare against Curve reference: the `get_y` function iterates over ALL pool balances except the target token.
4. Test: in a 3-token pool, check if A-B swaps produce different slippage than B-C swaps with identical pool composition — they should be equivalent in a correct implementation.
**Red flags**:
- `compute_swap(n_coins=3, offer_pool, ask_pool, ...)` but D is computed from only `offer_pool + ask_pool`
- `calculate_stableswap_d(offer_pool, ask_pool)` — sum uses 2 values but `ann = amp * n_coins` uses 3
- The `pool_sum` or `sum_pools` variable only includes 2 token balances
- D/y functions accept only 2 pool amounts as parameters despite being called for pools with 3+ tokens
- Different token-pair swaps in the same pool produce inconsistent pricing

### SS-3: Missing Imbalanced Deposit Fee
**Provenance**: drozer-lite v0.4.2 — class-of-bug: a StableSwap pool allows liquidity deposits at any ratio without charging a fee proportional to the imbalance (skew) introduced. In Curve's implementation, depositing in a ratio that deviates from the pool's current ratio incurs a fee equal to the swap fee on the "difference" between the ideal and actual deposit. Without this fee, users can skew the pool for free, manipulating the price at minimal cost.
**Pattern**: The LP minting function computes shares as `total_supply * (D1 - D0) / D0` where D1 includes the new deposits and D0 is the pre-deposit invariant. Curve additionally computes per-token ideal balances (`ideal_balance = D1 * old_balance / D0`) and charges a fee on the `|ideal_balance - new_balance|` for each token. This fee is missing in the implementation — users can deposit one-sided or skewed liquidity without penalty.
**Methodology**:
1. In the LP minting function for StableSwap, check whether any fee is charged based on the imbalance of the deposit.
2. If the only calculation is `shares = total_supply * (D1 - D0) / D0` with no per-token fee computation, flag.
3. Test: deposit a large one-sided amount (e.g., 2x of token A, 0 of token B). Compare the cost (shares received / value deposited) against a balanced deposit. In a correct implementation, the one-sided deposit should receive fewer shares due to the imbalance fee.
**Red flags**:
- `compute_lp_mint_amount = total_supply * (D1 - D0) / D0` — no per-token fee calculation
- No `ideal_balance`, `difference`, or `dynamic_fee` computation anywhere in the LP mint path
- One-sided deposit of 2x tokenA costs less than 0.5% in slippage — should cost at least the swap fee (e.g., 3-5%) on the skewed portion
- A user can skew the pool ratio dramatically with a deposit, then withdraw balanced, capturing value from other LPs

### SS-4: Newton-Raphson Non-Convergence Returns Result Instead of Error
**Provenance**: drozer-lite v0.4.2 — class-of-bug: the Newton-Raphson iterative solver for the StableSwap invariant D or pool balance y returns the last computed value even when the iteration limit is reached without convergence. A non-converged result is mathematically incorrect and produces wrong swap prices.
**Pattern**: The D or y computation uses a loop with a fixed iteration cap (e.g., 32, 256, 1000). On each iteration, it checks if `|current - previous| <= 1`. If the loop completes without converging, the function returns the last value instead of an error. In a correct implementation (Curve reference), non-convergence raises an error and the swap/deposit fails — only withdrawals remain functional, protecting LPs.
**Methodology**:
1. For every Newton-Raphson loop, check what happens after the loop ends WITHOUT convergence (i.e., the break condition was never met).
2. If the function returns `Some(last_value)` or `Ok(last_value)` after the loop, flag. It should return `None`, `Err(ConvergeError)`, or equivalent.
3. Check whether there are two D computation functions with different iteration caps (e.g., 32 for swaps, 256 for LP) — inconsistency flag per MATH-4.
4. Test with extremely imbalanced pools where convergence is slow — the function will return a wrong value instead of failing.
**Red flags**:
- Loop `for _ in 0..N { ... if converged { break; } }` followed by `Some(d)` outside the loop — always returns even if not converged
- No `return` or early exit on convergence — the `break` exits the loop and falls through to a successful return
- Correct pattern: convergence should `return Some(d)` inside the loop; after the loop, return `None` or `Err`
- Curve reference: `raise` after the loop (Python); the function never returns normally without convergence

### SS-5: Static Amplification Parameter (No Ramping Mechanism)
**Provenance**: drozer-lite v0.4.2 — class-of-bug: the StableSwap amplification parameter A is set once at pool creation and cannot be modified afterward. Curve's implementation includes a time-weighted ramping mechanism (`ramp_A` / `stop_ramp_A`) that allows the protocol to adjust A over time in response to market conditions. Without ramping, pools cannot adapt to depegging events and can leak value.
**Pattern**: The amplification parameter is stored as a static field in the pool configuration (e.g., `PoolType::StableSwap { amp: u64 }`). No `update_amp`, `ramp_A`, or similar function exists to modify it post-creation. During normal conditions, the pool works fine. During a depegging event (one stablecoin loses its peg), a high A value keeps the price artificially stable, allowing holders of the depegged asset to swap at near-1:1 rates and drain the pool of the healthy asset.
**Methodology**:
1. Check whether the amplification parameter can be modified after pool creation. Search for `ramp`, `update_amp`, `set_amp`, `modify_amp` in the execute message enum and handler.
2. If no modification mechanism exists, flag as MEDIUM — the pool cannot adapt to market conditions.
3. Check whether pool parameters are generally immutable post-creation (intentional design) or whether other parameters can be updated.
4. Assess the severity: if the DEX is designed for stablecoin pairs only, this is higher severity (depegging is the primary risk). If it supports volatile pairs via StableSwap (unusual), severity is lower.
**Red flags**:
- `PoolType::StableSwap { amp: u64 }` — static field, no update path
- No `ExecuteMsg::RampAmp` or `ExecuteMsg::UpdatePoolParams` in the message enum
- Pool fees can be set at creation but amp cannot be adjusted — asymmetric mutability
- Documentation mentions "stable assets" or "pegged assets" but no depeg protection mechanism
- Contrast with Curve: `ramp_A(future_A, future_time)` with `MIN_RAMP_TIME` safety constraint
