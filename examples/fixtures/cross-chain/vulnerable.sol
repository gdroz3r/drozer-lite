// SPDX-License-Identifier: MIT
// FIXTURE: vulnerable — cross-chain profile
// Bug: lzReceive() does not validate the source endpoint or the trusted
// remote, so any LayerZero endpoint can deliver a payload that mints tokens.
// Expected vulnerability_type: missing_destination_check / cross_chain_replay
pragma solidity ^0.8.0;

contract OmniToken {
    address public lzEndpoint;
    mapping(address => uint256) public balanceOf;

    constructor(address _endpoint) {
        lzEndpoint = _endpoint;
    }

    // BUG: setTrustedRemote is a no-op — the trusted remote map is never enforced.
    function setTrustedRemote(uint16, bytes calldata) external pure {}

    function bridge(uint16 dstChainId, address to, uint256 amount) external {
        balanceOf[msg.sender] -= amount;
    }

    function lzReceive(
        uint16 srcChainId,
        bytes calldata srcAddress,
        uint64 nonce,
        bytes calldata payload
    ) external {
        // No msg.sender == lzEndpoint check.
        // No trustedRemote[srcChainId] == srcAddress check.
        (address to, uint256 amount) = abi.decode(payload, (address, uint256));
        balanceOf[to] += amount;
    }
}
