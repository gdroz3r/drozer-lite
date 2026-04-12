# DEX Checklist

> Profile: dex
> Checks: 11
> Source: ported from Drozer-v2 dex-invariants.md + amm-invariants.md (provenance cited per check)

## Methodology

DEXes and AMMs expose user trades to MEV, sandwich, and price-manipulation attacks. For every swap / route / quote path, verify: (a) user-specified minOut / maxIn bounds are enforced AFTER the final hop, (b) deadlines are checked, (c) the AMM invariant (k = x·y, StableSwap D, or Balancer weighted) is preserved or increased, (d) prices used for critical decisions are manipulation-resistant (TWAP, oracle), and (e) routers never hold user tokens across transactions and never use `balanceOf` for balance-based accounting. Test each weird-token class (fee-on-transfer, rebasing, non-bool return) against the swap/add-liquidity path.

## Checks

### DEX-1: Slippage & Deadline Enforcement
**Provenance**: dex-invariants.md D1 + amm-invariants.md A9
**Pattern**: `amountOutMin` / `amountInMax` / `deadline` are accepted but not enforced on every swap path, or enforced only on intermediate hops.
**Methodology**: For every entry function (swap, swapExactTokensForTokens, multihop), verify the minOut check occurs AFTER all hops complete. Verify `require(block.timestamp <= deadline)`. For multihop, verify intermediate tokens cannot be stolen by a callback.
**Red flags**:
- Slippage check in the single-hop helper not re-executed for multihop
- `deadline` parameter but no check in code
- Final minOut compared to intermediate hop output

### DEX-2: Route Integrity & Intermediate Token Safety
**Provenance**: dex-invariants.md D2
**Pattern**: A multihop router holds intermediate tokens between hops; a malicious intermediate pool or callback redirects them to the attacker.
**Methodology**: For each hop, verify the output is forwarded to the next hop's input address (not left on the router). Verify callbacks cannot call back into the router with the balance available. Verify the declared path matches the executed path.
**Red flags**:
- Router uses `balanceOf(this)` as the amount for the next hop
- `_swap` pulls from and pushes to `address(this)` without a guard
- Callback invocation during a multihop route not reentrancy-protected

### DEX-3: Constant-Product / StableSwap Invariant Preservation
**Provenance**: amm-invariants.md A1
**Pattern**: Rounding errors or reentrancy allow `k` to decrease below its pre-swap value, leaking value out of the pool.
**Methodology**: For Uniswap V2 style: verify `k_after >= k_before` in `_update`. For Curve StableSwap: verify D is non-decreasing. For Balancer weighted: verify weighted balances satisfy the invariant.
**Red flags**:
- Swap math using `divide-before-multiply`
- k-check omitted because "impossible in normal flow"
- Flash-swap path that decreases k before the callback

### DEX-4: TWAP Oracle Integrity
**Provenance**: amm-invariants.md A4 + dex-invariants.md D5
**Pattern**: Oracle consumers use a single-block spot price or a TWAP with too short a window, allowing flash-loan manipulation.
**Methodology**: For every price consumer, identify the window. Test whether a same-block manipulation changes the reported price. Verify accumulator overflow handling.
**Red flags**:
- `getSpotPrice()` used for liquidation decisions
- TWAP window < 30 min for critical decisions
- Observations array too small to cover required lookback

### DEX-5: Flash Swap Repayment Enforcement
**Provenance**: amm-invariants.md A6
**Pattern**: Flash swap / flash loan callback fails to enforce repayment + fee, or does so only in the happy path.
**Methodology**: For each `flash`/`flashSwap`/`uniswapV2Call` path, trace the repayment check. Verify it compares pool balance after the callback against required amount + fee. Verify reentrancy guard covers the callback.
**Red flags**:
- Repayment check uses `balanceOf` trusting caller-provided amount
- Callback that can re-enter `flash` itself

### DEX-6: Token Approval Safety & Weird Tokens
**Provenance**: dex-invariants.md D4 + D9
**Pattern**: Router accepts fee-on-transfer / rebasing / non-bool-return tokens but computes amounts from `amount parameter` instead of actual received; or assumes infinite approval is safe.
**Methodology**: For each `transferFrom` path, verify actual received is measured via balance-before/after (not input amount). Verify `SafeERC20` or low-level success check is used. Verify approvals use `increaseAllowance` or reset-to-zero pattern.
**Red flags**:
- `token.transferFrom(user, pool, amount); _swap(amount, ...);` (no fee-on-transfer handling)
- Router holds user approvals permanently
- Permit handling that does not cover DAI's non-standard interface

### DEX-7: Pool Formula / Token-Count Mismatch
**Provenance**: drozer-lite v0.4.2 — class-of-bug: an AMM pool type uses a mathematical formula that assumes a fixed number of tokens (e.g., x*y=k for 2 tokens) but the pool creation function allows more tokens than the formula supports, producing incorrect swap results and broken invariants.
**Pattern**: A DEX supports multiple pool types (constant product, stable swap, weighted). Each pool type's swap formula is designed for a specific number of tokens. The pool creation function validates the token count against a global max (e.g., MAX_ASSETS = 4) but does NOT validate against the pool-type-specific maximum. A constant-product pool can be created with 3+ tokens even though the x*y=k formula only works for 2 tokens.
**Methodology**:
1. For each pool type, identify the mathematical formula used for swaps.
2. Determine how many tokens the formula supports: constant product (x*y=k) = 2; Balancer weighted = N; StableSwap = N.
3. Check whether pool creation enforces the pool-type-specific token limit. If a constant-product pool can be created with >2 tokens, flag as HIGH.
4. Check slippage tolerance assertions — if they hardcode `deposits.len() == 2` but the check is conditional (e.g., only runs when slippage_tolerance is Some), the guard can be bypassed.
**Red flags**:
- `MAX_ASSETS_PER_POOL = 4` applied uniformly to both constant-product and stable-swap pools
- Constant-product swap formula uses only `offer_pool` and `ask_pool` (2 tokens) but pool has 3+ tokens
- Slippage check requires exactly 2 deposits but is inside `if let Some(slippage_tolerance)` — bypassed when None
- Liquidity addition works for N tokens but shares calculated via `sqrt(d0 * d1)` (2-token formula)
- Pool creation validates `len >= 2 && len <= MAX` but not `if ConstantProduct then len == 2`

### DEX-8: Withdrawal Path Lacks Minimum-Output Protection
**Provenance**: drozer-lite v0.4.2 — class-of-bug: a liquidity withdrawal function calculates refund amounts proportionally but provides no mechanism for the user to specify minimum acceptable amounts, exposing them to sandwich attacks and unfavorable rates during high volatility.
**Pattern**: A `withdraw_liquidity` / `remove_liquidity` function burns LP tokens and returns underlying assets proportionally. The refund amounts are computed from the pool's current asset ratios. No `min_amount_out` or `minimum_receive` parameter exists. Industry standard (Uniswap V2 Router) provides `amountAMin` and `amountBMin` parameters for withdrawal protection.
**Methodology**:
1. For every liquidity withdrawal function, check whether the user can specify minimum acceptable output amounts.
2. If no minimum-output parameter exists, check whether slippage tolerance is applied to the withdrawal calculation.
3. If neither exists, flag. The user has no protection against pool composition changes between transaction submission and execution.
**Red flags**:
- `withdraw_liquidity(pool_id)` with no `min_assets_out` parameter
- Refund calculated as `pool_asset.amount * share_ratio` with no floor check
- No deadline parameter on withdrawal
- User must accept whatever the pool ratio is at execution time

### DEX-9: Asset Ordering Inconsistency Between Input and Internal State
**Provenance**: drozer-lite v0.4.2 — class-of-bug: user-provided deposit assets are sorted (by the chain or by aggregation logic) but pool-internal asset arrays maintain creation-time order. When slippage/ratio checks compare deposits[i] against pool_assets[i], the indices don't align, causing the check to use inverted ratios.
**Pattern**: A DEX pool stores assets in the order they were provided at creation time (e.g., [tokenB, tokenA]). User deposits are sorted alphabetically by the chain's coin handling or by an aggregation function (e.g., [tokenA, tokenB]). Slippage tolerance or ratio checks compare `deposits[0]/deposits[1]` against `pool_assets[0]/pool_assets[1]`. Because the orderings differ, the ratio comparison is inverted — checking the wrong price direction.
**Methodology**:
1. Check whether pool creation sorts `asset_denoms` or preserves caller-provided order.
2. Check whether `info.funds` / deposits are sorted (CosmWasm sorts funds alphabetically).
3. Check whether slippage/ratio checks index into both arrays positionally — if orderings can differ, the check is inverted.
4. A malicious pool creator can deliberately create a pool with reverse-ordered denoms to exploit this.
**Red flags**:
- `create_pool(asset_denoms: vec!["tokenB", "tokenA"])` — pool stores in this order
- Deposits arrive as `[tokenA, tokenB]` (chain-sorted)
- Slippage check: `deposits[0]/deposits[1] vs pool_assets[0]/pool_assets[1]` — inverted ratio
- Pool creation does not sort `asset_denoms` alphabetically
- Two pools with the same tokens but different ordering have different slippage behavior

### DEX-10: Disproportionate Deposit Loss (Excess Not Refunded)
**Provenance**: drozer-lite v0.4.2 — class-of-bug: when a user provides liquidity in a ratio different from the pool's current ratio, LP shares are minted based on the MINIMUM proportional share, and the excess tokens from the higher-ratio asset are effectively donated to the pool instead of being refunded.
**Pattern**: A `provide_liquidity` function calculates per-asset share ratios (`deposit_amount * total_share / pool_amount`) and mints LP tokens based on `min(share_ratios)`. The excess tokens from the non-minimum asset are added to the pool but not reflected in the minted shares. These excess tokens are permanently donated to all existing LPs. The function does NOT refund the excess to the depositor.
**Methodology**:
1. For every liquidity provision function, check how shares are computed when deposit ratios don't match pool ratios.
2. If `min(share_ratios)` is used, calculate the implied excess for each asset.
3. Check whether the excess is: (a) refunded to the depositor, (b) used to compute additional shares, or (c) silently donated to the pool.
4. If (c), check whether slippage tolerance protects against this loss. Note: slippage tolerance checks LP tokens received, NOT whether excess tokens are returned.
**Red flags**:
- `share = min(deposit_A * total_share / pool_A, deposit_B * total_share / pool_B)` with no refund of the difference
- User deposits 100A + 200B into a 1:1 pool; receives shares worth 100A + 100B; 100B is donated
- Slippage tolerance passes because LP tokens are within tolerance — but user lost 100B
- No industry-standard `_addLiquidity` that computes optimal amounts before the actual deposit (cf. Uniswap V2 Router)
- A front-runner changes the pool ratio between tx submission and execution, maximizing the user's excess donation

### DEX-11: Spread / Slippage Computed Before Fee Deduction
**Provenance**: drozer-lite v0.4.2 — class-of-bug: the spread or slippage amount is calculated from the pre-fee return amount, making the computed spread larger than the actual slippage. This causes the slippage check to be systematically too lenient, passing swaps that should have been rejected.
**Pattern**: A swap function computes `return_amount` (before fees), then `spread_amount = expected_return - return_amount`. Fees are then deducted from `return_amount` to get `final_return`. The `spread_amount` is compared against `max_spread`. Because `spread_amount` is computed before fees, it INCLUDES the fee as part of the "spread." The actual price slippage (excluding fees) is smaller than the reported `spread_amount`, making the spread check pass when the real slippage exceeds the user's tolerance.
**Methodology**:
1. In the swap computation, identify where `spread_amount` is calculated relative to fee deduction.
2. If `spread_amount = expected - return_amount` and `return_amount` is PRE-fee, the spread includes fees.
3. Check whether the spread check (`assert_max_spread`) uses this inflated spread or the actual post-fee slippage.
4. The correct approach: compute spread AFTER fees, or compute spread as `expected_return - (return_amount - fees)`.
**Red flags**:
- `spread_amount = offer_amount * exchange_rate - return_amount` where `return_amount` is before fees
- `assert_max_spread(spread_amount, return_amount + spread_amount)` — spread includes fees
- For StableSwap: `spread_amount = offer_amount - return_amount` (1:1 assumption) computed before fees
- Fees are 5-10% but spread check uses 1% tolerance — the fee inflates the spread past the tolerance, so the check effectively allows ~15% real slippage with a 1% setting
