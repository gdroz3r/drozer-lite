// SPDX-License-Identifier: MIT
// FIXTURE: vulnerable — governance profile
// Bug: castVote() reads voting power from the voter's CURRENT balance instead
// of a snapshot at proposal creation. A holder can vote, transfer the NFT,
// and the new owner can vote again on the same proposal.
// Expected vulnerability_type: signature_replay (vote_replay variant)
pragma solidity ^0.8.0;

interface IVoteNFT {
    function balanceOf(address) external view returns (uint256);
}

contract Governor {
    IVoteNFT public voteNFT;
    uint256 public quorum = 100;
    mapping(uint256 => mapping(address => bool)) public hasVoted;
    mapping(uint256 => uint256) public votesFor;
    mapping(address => uint256) public votingPower;

    constructor(IVoteNFT _voteNFT) {
        voteNFT = _voteNFT;
    }

    function castVote(uint256 proposalId) external {
        require(!hasVoted[proposalId][msg.sender], "already voted");
        uint256 power = voteNFT.balanceOf(msg.sender);
        require(power > 0, "no power");
        hasVoted[proposalId][msg.sender] = true;
        votesFor[proposalId] += power;
    }
}
