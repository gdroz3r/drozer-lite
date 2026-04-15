# Signature Checklist

> Profile: signature
> Checks: 4
> Source: ported from Drozer-v2 analyses (provenance cited per check)

## Methodology

Signatures authorize specific actions. An attacker controls what is NOT in the digest. For every ecrecover / EIP-712 / permit / isValidSignature call site, build a SIGNED DATA BINDING TABLE: list every field the function uses post-verification, mark each as signed (YES/NO), and mark each as caller-controllable (YES/NO). Every (Signed=NO, Used=YES, Caller-controlled=YES) row is a finding. Always check domain separation (chainId, verifyingContract), nonce/replay, and recipient/target binding. Attackers will front-run permit signatures from the mempool and reuse them in different execution contexts.

## Checks

### SIG-1: Digest Coverage Inventory (Unsigned Execution-Affecting Fields)
**Provenance**: signed-data-completeness.md §1 (maps to original AC-16 / APPROVAL-4)
**Pattern**: A function verifies a signature over a digest but decisions made after verification use fields that are not part of the signed bytes. Unsigned metadata (deadline, mode flags, gas parameters, callback data, recipients, amounts) can be substituted by a relayer, bundler, or MEV searcher without invalidating the signature.
**Methodology**: For every `ecrecover`, `ECDSA.recover`, `_hashTypedDataV4`, `SignatureChecker.isValidSignatureNow`, and any custom verification, identify the exact bytes being hashed. Build the SIGNED DATA BINDING TABLE. For every field used after verification, check whether it is inside the hashed payload. For each unsigned-but-used field, ask whether a relayer/bundler/MEV searcher can choose or modify it. Common unsigned fields: validity window, execution mode flags, gas parameters, callback data, auxiliary metadata.
**Red flags**:
- `deadline` read after verification but not in `_hashTypedDataV4` struct
- `callGasLimit`/`verificationGasLimit` consumed by executor but absent from the digest
- Oracle timestamp passed alongside but not inside the signed attestation
- ERC-4337 UserOp fields (paymasterAndData, maxFeePerGas) not part of `userOpHash`

### SIG-2: Domain Separation (Cross-Chain / Cross-Contract Replay)
**Provenance**: signed-data-completeness.md §2 (maps to original SEM-14 — was SOL-14 in solidity-semantics)
**Pattern**: Signatures are replayable across chains or across sibling contracts because the EIP-712 domain separator is missing, incomplete, or hardcoded.
**Methodology**: For every EIP-712 construction, verify the domain includes `chainId` AND `verifyingContract`. Verify the domain separator is recomputed (or cached with a chainId guard) to survive hard forks. For each `typeHash`, verify different operation types use distinct struct hashes to prevent operation confusion.
**Red flags**:
- Hardcoded `DOMAIN_SEPARATOR` without `block.chainid` recompute
- Missing `verifyingContract` in the EIP-712 domain struct
- Shared `typeHash` across unrelated operations
- Multi-contract system where a signature for contract A is accepted by contract B with identical code

### SIG-3: Recipient / Target Binding (Metadata & Beneficiary)
**Provenance**: signed-data-completeness.md §3 + §5 (maps to original DEFI-48)
**Pattern**: A signed message authorizes a value transfer or approval, but the recipient, target contract, or beneficiary is not in the signed payload. An intermediary substitutes the recipient to redirect value.
**Methodology**: For every signed operation that transfers or approves value, verify the recipient/spender/target address is part of the digest. For meta-transactions and account abstraction, verify the target contract is signed. For multi-hop operations, verify the FINAL recipient (not just the next hop) is bound. For `msg.sender`-dependent paths, verify the relayer cannot substitute themselves for the signer.
**Red flags**:
- `permit` with unsigned `spender`
- Meta-tx where `to` in the outer call is chosen by the relayer
- Bridge payload where `destination` is signed but `recipient` is not
- Account abstraction `beneficiary` in `handleOps` substituted by bundler

### SIG-4: Nonce & Replay Prevention Atomicity
**Provenance**: signed-data-completeness.md §4 (maps to original SEM-14 variant tracking nonce semantics)
**Pattern**: Signed messages can be replayed because the nonce is missing, not part of the digest, incremented non-atomically, or scoped too broadly (2D nonce key reused across operation types).
**Methodology**: Verify every signature mechanism has a nonce or unique identifier. Verify the nonce is part of the signed bytes (not just compared separately). Verify the nonce increments in the same transaction as verification (no gap). For 2D nonce schemes, verify keys cannot collide across operation types. For deadline-only replay protection, verify the window is tight AND the operation is idempotent.
**Red flags**:
- Nonce checked but not hashed into the digest
- `nonce++` in a different transaction than `ecrecover`
- 2D nonce key that is meaningful for op A but arbitrary for op B
- Batch operation with one nonce gating N independent items
