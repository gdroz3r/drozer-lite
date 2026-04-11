# DEX checklist

Triggered when the source contains swap, addLiquidity, amountOutMin, or Uniswap V2/V3 patterns.

> **Status:** Build Phase 1 placeholder. Content ported in Build Phase 2 from the main drozer dex profile.

Categories (to be expanded):

- Slippage protection (missing amountOutMin, deadline enforcement)
- Oracle manipulation (TWAP length, flash-loan manipulation)
- Sandwich attack surfaces (user-controlled reserves, MEV extraction)
- Price calculation (decimal assumptions, sqrtPriceX96 overflow)
- Fee tier confusion (pool selection for multi-fee routers)
- Callback reentrancy (Uniswap V3 swap callback, flash loan callback)
