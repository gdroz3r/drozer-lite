# Signature checklist

Triggered when the source contains EIP-712, permit, ecrecover, or EIP-2771 forwarder patterns.

> **Status:** Build Phase 1 placeholder. Content ported in Build Phase 2 from the Superfluid gap-fix lessons (SF001–SF004) and the main drozer signature-verification niche agent.

Categories (to be expanded):

- Digest binding (macro/contract address not in the digest, enabling cross-macro replay)
- Unsigned fields (executor-chosen parameters not covered by the witness)
- Nonce management (ERC-4337 key/sequence semantics, cross-account griefing)
- Cross-chain replay (missing chainId in domain separator)
- Permit2 witness coverage (transferDetails, upgradeSuperToken, spender)
- EIP-2771 attribution (sender suffix append, trusted forwarder verification)
