# DEX Checklist

> Profile: dex
> Checks: 6
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
