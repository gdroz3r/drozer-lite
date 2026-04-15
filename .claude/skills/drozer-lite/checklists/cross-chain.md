# Cross-Chain Checklist

> Profile: cross-chain
> Checks: 13
> Source: ported from Drozer-v2 bridge-invariants.md (provenance cited per check)

## Methodology

Cross-chain protocols have two adversaries: an attacker on the source chain trying to mint value on the destination without a valid lock, and an attacker on the destination trying to replay, spoof, or redirect messages. For every message path, identify (a) the trust model (validators, zk proof, multisig), (b) how finality is enforced, (c) every field that is attacker-controllable in the payload, and (d) whether the callback verifies the source-chain sender (not just the local bridge caller). Use bridge-specific chain IDs, not EVM chain IDs, for every bridge API call. Refund addresses must resolve to the actual user, not the intermediary contract.

## Checks

### XCHAIN-1: Token Supply Conservation
**Provenance**: bridge-invariants.md B1
**Pattern**: Tokens can be minted on the destination chain without a verified lock on the source chain, or unlocked on the source without a verified burn on the destination.
**Methodology**: For each mint/unlock path, trace the proof of the counterpart action. Verify proof validation is complete (not just signature presence). Verify there is no admin path that mints without a proof.
**Red flags**:
- `mint(to, amount)` gated only by `onlyRelayer` with no proof validation
- Admin emergency mint without supply reconciliation

### XCHAIN-2: Message Verification Integrity
**Provenance**: bridge-invariants.md B2
**Pattern**: Messages can be forged due to incomplete signature verification, missing source chain identification, or unauthorized sender acceptance.
**Methodology**: For each message-processing function, verify signature/validator-set verification, source chain check, and sender authorization. Each field used for decisions post-verification must be part of the signed bytes.
**Red flags**:
- `executeMessage(bytes payload)` without verifying payload author
- Source chain not part of the signed digest
- Sender verification uses `msg.sender` instead of the cross-chain sender

### XCHAIN-3: Replay Attack Prevention
**Provenance**: bridge-invariants.md B4
**Pattern**: The same message can be executed more than once (same chain, different chains, or across contract upgrades).
**Methodology**: Verify every message has a nonce / unique hash tracked in a "consumed" mapping. Check whether the consumed set survives upgrades. For multi-chain systems, verify domain separation.
**Red flags**:
- Nonce scope too narrow (per-user but not per-operation)
- `executedMessages` mapping cleared on upgrade
- Same payload valid on multiple destination chains

### XCHAIN-4: Finality & Reorg Handling
**Provenance**: bridge-invariants.md B5
**Pattern**: The destination chain processes a source-chain message before source-chain finality, losing funds after a reorg.
**Methodology**: Verify confirmation-blocks are set per source chain. Verify pending messages can be cancelled on reorg. Check finality assumption matches each chain's actual finality.
**Red flags**:
- 1-block confirmation on PoW source chain
- No reorg handling mechanism
- Static confirmation count across all chains

### XCHAIN-5: Validator / Relayer Threshold Integrity
**Provenance**: bridge-invariants.md B3
**Pattern**: Threshold signatures are validated incorrectly, validator-set updates are not authenticated, or a single compromised key can pass the check.
**Methodology**: Verify signatures are collected and validated against the current validator set with the correct threshold. Verify validator-set updates are authenticated (same threshold as normal messages). Check for slashing or off-chain penalty mechanism.

### XCHAIN-6: Token Mapping Integrity
**Provenance**: bridge-invariants.md B6
**Pattern**: Token mappings between chains can be set to wrong addresses or to malicious tokens, or decimal mismatches cause value drift.
**Methodology**: Verify token mapping setters are behind timelock + access control. Verify decimal normalization between chains. Verify no wrapped token can be registered without the protocol's acknowledgement.

### XCHAIN-7: Rate Limiting & Caps
**Provenance**: bridge-invariants.md B7
**Pattern**: A single transaction or short burst can drain the entire bridge because per-tx or per-period caps are missing.
**Methodology**: Verify per-tx and per-period limits exist on minting and unlocking. Verify rate windows cannot be reset by admin mid-attack.

### XCHAIN-8: Emergency Pause & Recovery
**Provenance**: bridge-invariants.md B8
**Pattern**: A guardian can pause the bridge, but the pause does not stop all value-moving paths, or the recovery path is insecure.
**Methodology**: Verify `pause()` gates every critical function. Verify no admin path circumvents the pause. Check recovery flows.

### XCHAIN-9: LP Protection (Liquidity-Network Bridges)
**Provenance**: bridge-invariants.md B9
**Pattern**: A liquidity-network bridge allows LPs to be drained via fake claims or sandwich attacks on deposits.
**Methodology**: For each LP deposit and withdrawal path, check for delay mechanisms and sandwich protection. Verify fee distribution is pro-rata and cannot be gamed.

### XCHAIN-10: Upgrade Safety for Bridges
**Provenance**: bridge-invariants.md B10
**Pattern**: Upgrades leave pending messages stranded, cause storage collisions, or reset the validator set to an insecure default.
**Methodology**: Verify upgrade path has timelock and handles in-flight messages. Verify storage layout compatibility and validator-set preservation.

### XCHAIN-11: Bridge Callback Source Verification
**Provenance**: bridge-invariants.md B11
**Pattern**: Callbacks (`onTokenBridged`, `lzReceive`, `ccipReceive`, `sgReceive`, `receiveWormholeMessages`) trust `msg.sender` (the bridge contract) without verifying the source-chain sender, allowing arbitrary users to craft fake instructions.
**Methodology**: For each callback, verify it calls the bridge's source-sender accessor (`messageSender()`, `_srcAddress`, etc.) and validates it against an expected remote. For bridges that do not expose the source sender in the token callback (e.g., Omnibridge `onTokenBridged`), verify token bridging and instruction bridging are separated.
**Red flags**:
- `function lzReceive(...)` that uses only `require(msg.sender == endpoint)` and trusts the payload
- `onTokenBridged` that treats the `data` bytes as authenticated

### XCHAIN-12: Bridge API Parameter Correctness (Chain IDs, Refund Addresses)
**Provenance**: bridge-invariants.md B12
**Pattern**: Calls to bridge APIs use EVM `block.chainid` where the bridge expects its own ID system (Wormhole uint16 chain IDs, LayerZero endpoint IDs), or use `msg.sender` as refund when funds should return to the end user.
**Methodology**: For each bridge API call, verify chain ID uses the bridge's own system. Verify refund addresses resolve to the end user (tx.origin in multi-hop chains, or user param), not `msg.sender`. On Arbitrum, verify `callValueRefundAddress` is not attacker-controllable (holds cancellation power over retryable tickets).

### XCHAIN-13: Bridge Value Handling (msg.value Surplus & Requirements)
**Provenance**: bridge-invariants.md B13
**Pattern**: `msg.value` is sent to a bridge that does not need ETH, or excess `msg.value - cost` is left in the contract instead of refunded to the user, or the bridge reverts because `msg.value < cost`.
**Methodology**: For each bridge type, verify whether ETH payment is required (some bridges use L1 gas escrow). Verify `msg.value >= cost` before the call and `msg.value - cost` is explicitly refunded to the actual user. Verify refund defaults do not route to an intermediary.
**Red flags**:
- `bridge.send{value: msg.value}(...)` to a bridge that uses L1 gas
- Excess left in the contract after `bridge.quote()`
- Refund to `msg.sender` when `msg.sender` is a router contract
