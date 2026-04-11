// SPDX-License-Identifier: MIT
// FIXTURE: vulnerable — reentrancy profile
// Bug: classic CEI violation. The external call to msg.sender happens before
// the balance is decremented. The contract also accepts NFT escrow via
// onERC721Received, so the same withdraw flow is reachable from a malicious
// receiver hook.
// Expected vulnerability_type: reentrancy
pragma solidity ^0.8.0;

abstract contract ReentrancyGuard {
    uint256 private _status;
    modifier nonReentrant() {
        require(_status == 0, "REENTRANT");
        _status = 1;
        _;
        _status = 0;
    }
}

contract NftEscrow is ReentrancyGuard {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // BUG: nonReentrant is NOT applied here.
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "send failed");
        balances[msg.sender] -= amount;
    }

    function onERC721Received(
        address,
        address,
        uint256,
        bytes calldata
    ) external pure returns (bytes4) {
        return this.onERC721Received.selector;
    }
}
