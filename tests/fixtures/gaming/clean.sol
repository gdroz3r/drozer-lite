// SPDX-License-Identifier: MIT
// FIXTURE: clean — gaming profile
// Uses Chainlink VRF (sketched) for randomness instead of block fields.
pragma solidity ^0.8.0;

interface VRFCoordinatorV2 {
    function requestRandomWords(
        bytes32 keyHash,
        uint64 subId,
        uint16 reqConfs,
        uint32 callbackGasLimit,
        uint32 numWords
    ) external returns (uint256 requestId);
}

contract Raffle {
    VRFCoordinatorV2 public vrf;
    address[] public participants;
    address public lastWinner;
    uint256 public pendingRequest;

    constructor(VRFCoordinatorV2 _vrf) {
        vrf = _vrf;
    }

    function enter() external payable {
        require(msg.value == 0.1 ether, "wrong fee");
        participants.push(msg.sender);
    }

    function drawWinner() external {
        require(participants.length > 0, "no participants");
        require(pendingRequest == 0, "already drawing");
        pendingRequest = vrf.requestRandomWords(bytes32(0), 1, 3, 200_000, 1);
    }

    function fulfillRandomWords(uint256 requestId, uint256[] memory randomWords) external {
        require(msg.sender == address(vrf), "not vrf");
        require(requestId == pendingRequest, "stale request");
        uint256 idx = randomWords[0] % participants.length;
        lastWinner = participants[idx];
        payable(lastWinner).transfer(address(this).balance);
        delete participants;
        pendingRequest = 0;
    }
}
