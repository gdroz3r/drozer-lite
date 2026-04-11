// SPDX-License-Identifier: MIT
// FIXTURE: vulnerable — math profile
// Bug: addReward mixes 18-decimal and 6-decimal token amounts in the same
// accumulator without scaling. The 6-decimal token contributes ~1e12x less
// reward than the 18-decimal one.
// Expected vulnerability_type: decimal_scaling_mismatch
pragma solidity ^0.8.0;

contract RewardPool {
    mapping(address => uint256) public rewards;
    uint256 public totalRewards;

    // amount18 is in 18-decimal units, amount6 in 6-decimal units.
    function addReward(address user, uint256 amount18, uint256 amount6) external {
        // BUG: amount6 is added without scaling to 18 decimals.
        uint256 reward = amount18 + amount6;
        rewards[user] += reward;
        totalRewards += reward;
    }
}
