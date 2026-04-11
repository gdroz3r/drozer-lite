// SPDX-License-Identifier: MIT
// FIXTURE: clean — math profile
// Scales 6-decimal input up to 18 decimals before accumulation.
pragma solidity ^0.8.0;

contract RewardPool {
    mapping(address => uint256) public rewards;
    uint256 public totalRewards;
    uint256 private constant SCALE_6_TO_18 = 1e12;

    function addReward(address user, uint256 amount18, uint256 amount6) external {
        uint256 amount6Scaled = amount6 * SCALE_6_TO_18;
        uint256 reward = amount18 + amount6Scaled;
        rewards[user] += reward;
        totalRewards += reward;
    }
}
