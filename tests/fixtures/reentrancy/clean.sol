// SPDX-License-Identifier: MIT
// FIXTURE: clean — reentrancy profile
// State updated before the external call AND nonReentrant is applied to withdraw.
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

    function withdraw(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "insufficient");
        balances[msg.sender] -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "send failed");
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
