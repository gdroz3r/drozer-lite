// SPDX-License-Identifier: MIT
// FIXTURE: clean — dex profile
// Caller-supplied amountOutMin and explicit deadline.
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

contract SafeSwap {
    IUniswapV2Router public router;

    constructor(IUniswapV2Router _router) {
        router = _router;
    }

    function swap(
        uint amountIn,
        uint amountOutMin,
        uint deadline,
        address[] calldata path
    ) external {
        require(amountOutMin > 0, "no slippage protection");
        require(deadline >= block.timestamp, "expired");
        router.swapExactTokensForTokens(amountIn, amountOutMin, path, msg.sender, deadline);
    }
}
