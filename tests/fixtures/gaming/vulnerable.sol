// SPDX-License-Identifier: MIT
// FIXTURE: vulnerable — gaming profile
// Bug: drawWinner() uses block.timestamp + block.number as randomness. A
// miner / proposer can predict and bias the outcome — classic lottery
// weak-randomness anti-pattern. Should use Chainlink VRF requestRandomWords.
// Expected vulnerability_type: timestamp_dependence (or weak_randomness)
pragma solidity ^0.8.0;

contract Raffle {
    address[] public participants;
    address public lastWinner;

    function enter() external payable {
        require(msg.value == 0.1 ether, "wrong fee");
        participants.push(msg.sender);
    }

    function drawWinner() external {
        require(participants.length > 0, "no participants");
        uint256 idx = uint256(keccak256(abi.encodePacked(block.timestamp, block.number)))
            % participants.length;
        lastWinner = participants[idx];
        payable(lastWinner).transfer(address(this).balance);
        delete participants;
    }
}
