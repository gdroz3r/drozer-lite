// SPDX-License-Identifier: MIT
// FIXTURE: clean — signature profile
// Adds a per-recipient nonce to the signed payload and increments it on claim.
pragma solidity ^0.8.0;

contract Airdrop {
    bytes32 public constant EIP712_TYPEHASH =
        keccak256("EIP712Domain(uint256 chainId,address verifyingContract)");
    bytes32 public DOMAIN_SEPARATOR;
    address public signer;
    mapping(address => uint256) public nonces;
    mapping(address => uint256) public claimed;

    constructor(address _signer) {
        signer = _signer;
        DOMAIN_SEPARATOR = keccak256(abi.encode(EIP712_TYPEHASH, block.chainid, address(this)));
    }

    function _hashTypedDataV4(bytes32 structHash) internal view returns (bytes32) {
        return keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
    }

    function claim(uint256 amount, uint256 nonce, bytes32 r, bytes32 s, uint8 v) external {
        require(nonce == nonces[msg.sender], "bad nonce");
        bytes32 digest = _hashTypedDataV4(keccak256(abi.encode(msg.sender, amount, nonce)));
        address recovered = ecrecover(digest, v, r, s);
        require(recovered == signer, "bad sig");
        nonces[msg.sender] = nonce + 1;
        claimed[msg.sender] += amount;
    }
}
