// SPDX-License-Identifier: MIT
// FIXTURE: clean — lending profile
// borrow() recalculates the borrower's health factor after the new debt and
// reverts if it would fall below the liquidation threshold.
pragma solidity ^0.8.0;

contract Lending {
    mapping(address => uint256) public collateral;
    mapping(address => uint256) public debtToken;
    uint256 public LTV = 75;

    function depositCollateral(uint256 amount) external {
        collateral[msg.sender] += amount;
    }

    function borrow(uint256 amount) external {
        uint256 newDebt = debtToken[msg.sender] + amount;
        require(_healthAfter(collateral[msg.sender], newDebt) >= 100, "would liquidate");
        debtToken[msg.sender] = newDebt;
        payable(msg.sender).transfer(amount);
    }

    function _healthAfter(uint256 col, uint256 debt) internal view returns (uint256) {
        if (debt == 0) return type(uint256).max;
        return (col * LTV) / debt;
    }

    function liquidate(address user) external {
        require(_healthAfter(collateral[user], debtToken[user]) < 100, "healthy");
        delete collateral[user];
        delete debtToken[user];
    }
}
