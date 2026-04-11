// SPDX-License-Identifier: MIT
// FIXTURE: vulnerable — dex profile
// Bug: swap() has no slippage protection (no amountOutMin), so it is sandwich-
// vulnerable.
// Expected vulnerability_type: missing_slippage_protection
pragma solidity ^0.8.0;

interface IUniswapV2Router {
    function swapExactTokensForTokens(
        uint amountIn,
        uint amountOutMin,
        address[] calldata path,
        address to,
        uint deadline
    ) external returns (uint[] memory amounts);
}

contract NaiveSwap {
    IUniswapV2Router public router;

    constructor(IUniswapV2Router _router) {
        router = _router;
    }

    function swap(uint amountIn, address[] calldata path) external {
        // amountOutMin set to 0 — no slippage protection
        router.swapExactTokensForTokens(amountIn, 0, path, msg.sender, block.timestamp);
    }
}
