// SPDX-License-Identifier: MIT
// FIXTURE: clean — governance profile
// Vote weight is read from a snapshot at proposal creation, not current balance.
pragma solidity ^0.8.0;

interface IVoteNFT {
    function balanceOfAt(address user, uint256 blockNumber) external view returns (uint256);
}

contract Governor {
    IVoteNFT public voteNFT;
    uint256 public quorum = 100;
    struct Proposal { uint256 snapshotBlock; uint256 votesFor; }
    mapping(uint256 => Proposal) public proposals;
    mapping(uint256 => mapping(address => bool)) public hasVoted;
    uint256 public nextId;

    constructor(IVoteNFT _voteNFT) {
        voteNFT = _voteNFT;
    }

    function propose() external returns (uint256 id) {
        id = ++nextId;
        proposals[id].snapshotBlock = block.number;
    }

    function castVote(uint256 proposalId) external {
        require(!hasVoted[proposalId][msg.sender], "already voted");
        Proposal storage p = proposals[proposalId];
        require(p.snapshotBlock != 0, "unknown proposal");
        uint256 power = voteNFT.balanceOfAt(msg.sender, p.snapshotBlock);
        require(power > 0, "no power");
        hasVoted[proposalId][msg.sender] = true;
        p.votesFor += power;
    }
}
