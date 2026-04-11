// SPDX-License-Identifier: MIT
// FIXTURE: clean — cross-chain profile
// Validates msg.sender == lzEndpoint and srcAddress == trustedRemote[srcChainId].
pragma solidity ^0.8.0;

contract OmniToken {
    address public lzEndpoint;
    mapping(uint16 => bytes) public trustedRemote;
    mapping(address => uint256) public balanceOf;

    constructor(address _endpoint) {
        lzEndpoint = _endpoint;
    }

    function setTrustedRemote(uint16 srcChainId, bytes calldata remote) external {
        trustedRemote[srcChainId] = remote;
    }

    function bridge(uint16 dstChainId, address to, uint256 amount) external {
        balanceOf[msg.sender] -= amount;
    }

    function lzReceive(
        uint16 srcChainId,
        bytes calldata srcAddress,
        uint64 nonce,
        bytes calldata payload
    ) external {
        require(msg.sender == lzEndpoint, "untrusted endpoint");
        bytes memory expected = trustedRemote[srcChainId];
        require(
            expected.length == srcAddress.length &&
                keccak256(expected) == keccak256(srcAddress),
            "untrusted remote"
        );
        (address to, uint256 amount) = abi.decode(payload, (address, uint256));
        balanceOf[to] += amount;
    }
}
