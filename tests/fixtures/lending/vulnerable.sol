// SPDX-License-Identifier: MIT
// FIXTURE: vulnerable — lending profile
// Bug: borrow() does not check the borrower's health factor / LTV after the
// debt is increased. A user can borrow more than their collateral supports.
// Expected vulnerability_type: missing_access_control (or LTV-related variant)
pragma solidity ^0.8.0;

contract Lending {
    mapping(address => uint256) public collateral;
    mapping(address => uint256) public debtToken;
    uint256 public LTV = 75;

    function depositCollateral(uint256 amount) external {
        collateral[msg.sender] += amount;
    }

    function borrow(uint256 amount) external {
        debtToken[msg.sender] += amount;
        payable(msg.sender).transfer(amount);
    }

    function healthFactor(address user) external view returns (uint256) {
        if (debtToken[user] == 0) return type(uint256).max;
        return (collateral[user] * LTV) / debtToken[user];
    }

    function liquidate(address user) external {
        require(this.healthFactor(user) < 100, "healthy");
        delete collateral[user];
        delete debtToken[user];
    }
}
