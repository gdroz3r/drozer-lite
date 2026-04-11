// SPDX-License-Identifier: MIT
// FIXTURE: vulnerable — vault profile
// Bug: ERC4626-style vault with no virtual shares/assets and no first-deposit
// guard. The first depositor can mint 1 wei share, donate the underlying to
// inflate convertToShares(), then later depositors get 0 shares.
// Expected vulnerability_type: share_inflation
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

    constructor(IERC20 _asset) {
        asset = _asset;
    }

    function totalAssets() public view returns (uint256) {
        return asset.balanceOf(address(this));
    }

    function convertToShares(uint256 assets) public view returns (uint256) {
        if (totalShares == 0) return assets;
        return (assets * totalShares) / totalAssets();
    }

    function deposit(uint256 assets) external returns (uint256 mintedShares) {
        mintedShares = convertToShares(assets);
        asset.transferFrom(msg.sender, address(this), assets);
        shares[msg.sender] += mintedShares;
        totalShares += mintedShares;
    }
}
