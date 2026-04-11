// SPDX-License-Identifier: MIT
// FIXTURE: clean — vault profile
// Uses virtual shares + virtual assets to make share inflation uneconomical.
pragma solidity ^0.8.0;

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address) external view returns (uint256);
}

contract Vault {
    IERC20 public asset;
    uint256 public totalShares;
    mapping(address => uint256) public shares;
    uint256 private constant VIRTUAL_SHARES = 1e6;
    uint256 private constant VIRTUAL_ASSETS = 1;

    constructor(IERC20 _asset) {
        asset = _asset;
    }

    function totalAssets() public view returns (uint256) {
        return asset.balanceOf(address(this));
    }

    function convertToShares(uint256 assets) public view returns (uint256) {
        return (assets * (totalShares + VIRTUAL_SHARES)) / (totalAssets() + VIRTUAL_ASSETS);
    }

    function deposit(uint256 assets) external returns (uint256 mintedShares) {
        require(assets > 0, "zero deposit");
        mintedShares = convertToShares(assets);
        require(mintedShares > 0, "zero shares");
        asset.transferFrom(msg.sender, address(this), assets);
        shares[msg.sender] += mintedShares;
        totalShares += mintedShares;
    }
}
