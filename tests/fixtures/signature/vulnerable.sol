// SPDX-License-Identifier: MIT
// FIXTURE: vulnerable — signature profile
// Bug: claim() verifies an EIP-712 signature but does not consume a nonce.
// The same signature can be replayed forever.
// Expected vulnerability_type: signature_replay
pragma solidity ^0.8.0;

contract Airdrop {
    bytes32 public constant EIP712_TYPEHASH =
        keccak256("EIP712Domain(uint256 chainId,address verifyingContract)");
    bytes32 public DOMAIN_SEPARATOR;
    address public signer;
    mapping(address => uint256) public claimed;

    constructor(address _signer) {
        signer = _signer;
        DOMAIN_SEPARATOR = keccak256(abi.encode(EIP712_TYPEHASH, block.chainid, address(this)));
    }

    function _hashTypedDataV4(bytes32 structHash) internal view returns (bytes32) {
        return keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
    }

    function claim(uint256 amount, bytes32 r, bytes32 s, uint8 v) external {
        bytes32 digest = _hashTypedDataV4(keccak256(abi.encode(msg.sender, amount)));
        address recovered = ecrecover(digest, v, r, s);
        require(recovered == signer, "bad sig");
        claimed[msg.sender] += amount;
    }
}
