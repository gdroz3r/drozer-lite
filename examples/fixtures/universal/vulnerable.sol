// SPDX-License-Identifier: MIT
// FIXTURE: vulnerable — universal profile
// Bug: setOwner has no access control. Anyone can become the owner.
// Expected vulnerability_type: missing_access_control
pragma solidity ^0.8.0;

contract Owned {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function setOwner(address newOwner) external {
        owner = newOwner;
    }

    function withdrawAll() external {
        require(msg.sender == owner, "not owner");
        payable(msg.sender).transfer(address(this).balance);
    }
}
