---
name: drozer-lite
description: General-purpose pattern-level Solidity vulnerability scanner with cross-file awareness. Walks any Solidity protocol (single contract or multi-file project), builds an inventory, clusters related contracts, applies a curated checklist of 180 vulnerability patterns derived from real benchmark gap analysis across 13 protocol-type profiles, and returns structured findings. USE WHEN the user asks to scan, audit, or review Solidity source for security bugs and wants pattern-level coverage. Designed for protocols up to ~500KB / 100 files. Wall-clock 5-30 min depending on size. Does NOT do multi-step actor reasoning, chain analysis, or formal verification — for that, use the full drozer pipeline (`/droz3r`).
---

# drozer-lite — open-source pattern-level Solidity auditor (v0.3.0, cluster mode)

You are about to run a multi-file pattern-level Solidity audit using drozer-lite's curated checklist. Follow this 8-step workflow exactly. Do not invent steps, do not paraphrase the checklist, do not invent findings.

drozer-lite is the open-source pattern-level slice of the main Drozer-v2 auditor. Every check in the bundled checklists traces to a real audit finding that was missed in past benchmark runs (Virtuals, Morph L2, Oku, Kinetiq, Superfluid, Perennial V2, AXION, Lendvest, and others). The provenance is cited inside each check.

drozer-lite is intentionally narrow:

- **Pattern-level checks** drawn from a curated checklist
- **Cross-file aware** (catches bugs spanning multiple contracts)
- Does NOT do multi-step actor reasoning, chain composition analysis, or formal verification — that's `/droz3r` territory

The trade-off is on purpose: drozer-lite finds the bugs pattern matching CAN find, fast and reproducibly, without pretending to be a full audit pipeline.

---

## Step 1 — Identify the target

Determine which file(s) the user wants audited.

- If the user pasted source inline, treat it as a one-file target.
- If the user referenced a path, walk it. Use Glob `**/*.sol` from that root.
- Filter out these directories anywhere in the path: `node_modules`, `lib`, `test`, `tests`, `mock`, `mocks`, `script`, `scripts`, `out`, `cache`, `.git`, `.forge`, `broadcast`, `coverage`.
- **Soft warning**: if total source > 500KB, tell the user "this will take ~30+ minutes" and continue.
- **Hard refusal**: if total source > 1MB, REFUSE. Recommend `/droz3r` (the full drozer pipeline).
- File suffixes: `.sol` only, unless `--profile icp` (Internet Computer / Rust) or `--profile solana` (Anchor / Rust) is explicitly passed.

If you cannot find any source, ask the user to specify a path or paste source. Do not guess.

---

## Step 2 — Build the inventory (cheap structural pass)

Read each in-scope file with the Read tool. Do NOT analyze code yet — only extract structure. Build an in-context inventory map covering:

For each file:
- **Path** and approximate byte size + line count
- **Contracts** declared (and what they extend)
- **External / public function signatures** (name + params + visibility + modifiers, no body)
- **State variables** (name + type + visibility)
- **Modifiers** declared in this contract
- **External calls visible**: `.call`, `.transfer`, `.send`, library calls, and named contract calls (e.g. `someContract.someFunction(...)`)
- **Imports** (which other in-scope files this file depends on)

Format the inventory like this (keep it terse — this is your context_map for cross-file detection):

```
INVENTORY (12 files, 100KB total):

KHYPE.sol (4.4KB, 119L)
  Contracts: KHYPE → ERC20PermitUpgradeable, AccessControlEnumerableUpgradeable
  External fns: initialize, mint(onlyRole(MINTER_ROLE)), burn(onlyRole(BURNER_ROLE)), supportsInterface, _update(whenNotPaused)
  State: pauserRegistry, MINTER_ROLE, BURNER_ROLE
  Modifiers: whenNotPaused
  External calls: pauserRegistry.isPaused(this)
  Imports: IPauserRegistry

StakingManager.sol (41KB, 1063L)
  Contracts: StakingManager → AccessControlEnumerableUpgradeable, ReentrancyGuardUpgradeable, IStakingManager
  External fns: initialize, stake (payable, nonReentrant, whenNotPaused, whenStakingNotPaused), queueWithdrawal (nonReentrant, whenNotPaused, whenWithdrawalNotPaused), confirmWithdrawal (nonReentrant, whenNotPaused), batchConfirmWithdrawals, processValidatorWithdrawals, processValidatorRedelegation, queueL1Operations, processL1Operations, ...
  State: validatorManager, pauserRegistry, stakingAccountant, kHYPE, treasury, totalStaked, totalClaimed, totalQueuedWithdrawals, hypeBuffer, targetBuffer, ...
  External calls: validatorManager.totalRewards(), stakingAccountant.HYPEToKHYPE(), kHYPE.mint(), payable(msg.sender).call{value: amount}, ...
  Imports: IValidatorManager, IStakingManager, IPauserRegistry, IStakingAccountant, KHYPE
```

The inventory is your context_map. Reference it during cluster analysis (Step 5) to detect cross-file bugs without loading every cluster's full source at once.

**Time budget for Step 2**: ~30 sec per file. For a 100KB / 9-file protocol like Kinetiq, ~5 minutes.

---

## Step 3 — Detect profiles (with always-load fallback)

Apply the keyword detection table below to the WHOLE inventory (not file-by-file). Detection is **case-insensitive**. A profile is **auto-loaded** if it scores **3 or more distinct keyword matches** across the inventory.

**ALWAYS LOAD**: `universal` (regardless of detection)

**Auto-detect** (per-profile threshold = 3 distinct patterns):

| Profile | Keywords (case-insensitive) |
|---|---|
| signature   | `EIP712`, `permit(`, `ecrecover(`, `isValidSignature`, `_hashTypedDataV4`, `DOMAIN_SEPARATOR`, `permitWitnessTransferFrom`, `_signTypedData`, `Permit2`, `IERC1271` |
| vault       | `ERC4626`, `totalAssets`, `previewDeposit`, `previewWithdraw`, `convertToShares`, `convertToAssets`, `function deposit(`, `function withdraw(`, `IERC4626`, `sharesOf`, `maxDeposit` |
| lending     | `borrow`, `liquidate`, `collateral`, `healthFactor`, `LTV`, `debtToken`, `interestRate`, `repay`, `supply(`, `IPool`, `ILendingPool`, `_borrow` |
| dex         | `swap`, `addLiquidity`, `removeLiquidity`, `amountOutMin`, `IUniswapV2`, `IUniswapV3`, `ISwapRouter`, `sqrtPriceX96`, `getAmountsOut`, `swapExactTokensFor`, `IPool` |
| cross-chain | `lzReceive`, `ccipReceive`, `setPeer`, `setTrustedRemote`, `wormhole`, `IReceiver`, `bridge(`, `ILayerZero`, `NonblockingLzApp`, `_nonblockingLzReceive`, `IRouterClient` |
| governance  | `propose(`, `castVote(`, `quorum`, `delegate(`, `Governor`, `Timelock`, `votingPower`, `IGovernor`, `_execute`, `getVotes`, `IVotes` |
| reentrancy  | `nonReentrant`, `ReentrancyGuard`, `.call{value`, `onERC721Received`, `onERC1155Received`, `tokensReceived`, `ERC777`, `IERC777Recipient`, `_checkOnERC721Received`, `IERC1155Receiver` |
| oracle      | `AggregatorV2Interface`, `AggregatorV3Interface`, `latestRoundData`, `latestAnswer`, `IChainlink`, `priceFeed`, `getPrice`, `oracle`, `IPyth`, `IOracle`, `OracleManager`, `oracleAdapter`, `IOracleAdapter`, `getValidatorMetrics`, `setOracle`, `_oracle`, `DefaultOracle`, `oracles/` |
| math        | `FixedPoint`, `PRBMath`, `mulDiv`, `SafeMath`, `WAD`, `RAY`, `UFixed`, `SD59x18`, `UD60x18`, `abdk`, `FullMath`, `MathUpgradeable` |
| gaming      | `VRFConsumerBase`, `VRFCoordinator`, `randomness`, `raffle`, `lottery`, `requestRandomWords`, `fulfillRandomWords`, `ChainlinkVRF`, `VRFV2`, `IVRFCoordinator` |

**EXPLICIT-ONLY** (never auto-load): `icp`, `solana`. Load only if the user passed `--profile icp` or `--profile solana` literally.

**Hard rule**: do not lower the threshold to "make a profile fire" because you intuit it might be relevant. If a profile genuinely does not clear the threshold, do not load its checklist. Pattern coverage IS the contract.

**Document the selection**. Output a "Profile Selection" block the user can read, listing every profile and its match count:

```
PROFILE SELECTION:
  universal     → ALWAYS LOADED
  reentrancy    → AUTO-LOADED (5 matches: nonReentrant, ReentrancyGuard, .call{value, onERC721Received, ERC777)
  oracle        → AUTO-LOADED (4 matches: oracle, OracleManager, IOracleAdapter, getValidatorMetrics)
  vault         → not loaded (0 matches)
  lending       → not loaded (0 matches)
  signature     → not loaded (1 match: ERC20PermitUpgradeable)
  ...
```

If the user disagrees, they can re-invoke with `--profile <name>` to force-load.

---

## Step 4 — Cluster the codebase

Group files into clusters of 1-5 files each. Target **30-50KB per cluster**. Use these rules in order:

1. **Inheritance chain** — files containing parent + child contracts go in the same cluster.
2. **Mutual import** — file A imports B, file B imports A → same cluster.
3. **Subdirectory + shared imports** — files in the same `oracles/`, `validators/`, `governance/` subdirectory with overlapping imports → same cluster.
4. **Single oversized file** — a file > 30KB becomes its own cluster. If it's > 60KB, you'll need to analyze it in two passes (top half / bottom half) and merge findings.
5. **Soft cap**: if a cluster exceeds 60KB, split it along the weakest dependency edge.

Output the cluster plan in a "CLUSTER PLAN" block:

```
CLUSTER PLAN:
  Cluster 1 — StakingCluster (54KB, 1.4K lines)
    Files: KHYPE.sol, StakingManager.sol, StakingAccountant.sol
    Dependencies: KHYPE imports IPauserRegistry; StakingManager imports KHYPE + IStakingAccountant; StakingAccountant imports IValidatorManager
  Cluster 2 — ControlCluster (24KB, 643 lines)
    Files: ValidatorManager.sol, PauserRegistry.sol
    Dependencies: ValidatorManager imports IPauserRegistry + IStakingManager
  Cluster 3 — OracleCluster (21KB, 542 lines)
    Files: OracleManager.sol, oracles/DefaultAdapter.sol, oracles/DefaultOracle.sol, oracles/IOracleAdapter.sol
    Dependencies: OracleManager imports IOracleAdapter; DefaultAdapter imports IOracleAdapter
```

---

## Step 5 — Per-cluster analysis

For each cluster:

1. **Read the cluster's source** — Read each file in the cluster fully.
2. **Read the relevant checklists** — Read `checklists/universal.md` always, plus each auto-loaded profile checklist (`checklists/{profile}.md`).
3. **Reference the inventory from Step 2** — for cross-cluster bug detection. When the cluster you're analyzing calls a function in another cluster, look up the target's signature in the inventory; you don't need to re-read the other cluster's full source.
4. **Apply each loaded check** — for each check in the loaded checklists, examine the cluster source. A check matches when ALL of:
   - The **Pattern** field describes a code construct that exists in the cluster source
   - The **Red flags** are visible in the source
   - The **Methodology** describes a reachable exploit path you can trace line by line
5. **When unsure, prefer NOT to report.** False positives are worse than misses. The user expects high signal, not coverage.
6. **For each match**, identify:
   - The affected function name and the file it lives in (full path within the project)
   - A specific line as the most representative location for `line_hint`
   - A severity from CRITICAL/HIGH/MEDIUM/LOW/INFO using the matrix below
   - A confidence from HIGH/MEDIUM/LOW based on how clearly the source matches the check
   - The check ID that fired (e.g. `UNI-1`, `RE-2`, `ORC-3`) — record this internally
7. **Add cluster metadata** to each finding: `cluster: "<cluster name>"`. The dedup pass will use this.
8. **Do not output yet** — accumulate findings in your working set. Output is at Step 7.

You may analyze clusters sequentially (recommended for token budget). Each cluster gets its own independent reasoning pass — but ALL clusters share the same checklist context that you loaded once at the start.

### Severity matrix

| Severity   | Criteria                                                                                  |
|------------|-------------------------------------------------------------------------------------------|
| CRITICAL   | Permissionless theft >$100k OR protocol-wide fund lock                                    |
| HIGH       | Theft with conditions OR significant fund lock                                            |
| MEDIUM     | Meaningful loss with setup requirements                                                    |
| LOW        | Limited impact, hard to exploit, or pure griefing                                          |
| INFO       | Best practice, hardening, non-exploitable                                                  |

### Confidence

- **HIGH**: code clearly matches the pattern; you can quote the offending line(s).
- **MEDIUM**: pattern is present but exploitability depends on context you cannot fully verify from the cluster alone.
- **LOW**: uncertain — match is suggestive, not definitive.

**Time budget for Step 5**: ~3-5 minutes per cluster of normal density. A 50KB cluster with all checks should be ~5 min. Skip checks that obviously don't apply (e.g., `permit_frontrun` on a contract with no signatures).

---

## Step 6 — Cross-cluster sweep

After all clusters are analyzed, look for bugs that span clusters. This is the step that catches the bugs single-cluster analysis misses.

For each pair of clusters (A, B) that have references in the inventory:

1. **State write/read mismatches**: function in cluster A writes state variable V; function in cluster B reads V without re-validating preconditions. Look for staleness.
2. **Cross-contract access control gaps**: cluster A function F is guarded by role R; cluster B has a wrapper W around F that has weaker or no access control. The wrapper bypasses the guard.
3. **Auto-route fallbacks**: cluster A's contract has a `receive()` or `fallback()` that calls a state-changing function in the same or another cluster, so the contract balance is never what callers expect. Check whether ANY function in the inventory uses `address(...).balance` for an invariant the auto-routing breaks.
4. **Service interface failure modes**: cluster A provides an interface (e.g., `IOracle`); cluster B consumes it without checking for stale, zero, or revert returns.
5. **Shared modifier inconsistency**: same bug class fires in cluster A but not B, even though both use the same modifier — flag the missing application in B.
6. **Pause-state asymmetry**: a pause flag in cluster A is checked in some functions but not in functionally-equivalent siblings in cluster B.

Use the **inventory from Step 2** to identify cross-cluster references quickly. You do NOT need to re-read full cluster source to do the sweep — the inventory has the structural information.

Add cross-cluster findings to the same finding pool with `cross_cluster: true` and the names of both clusters involved.

This is the v0.3.0 difference vs v0.2.0: the cross-cluster sweep catches Kinetiq-style auto-route bugs, cross-contract ACL gaps, and consumer-side oracle staleness misses that single-cluster analysis misses.

**Time budget for Step 6**: ~3-5 minutes for a Kinetiq-sized protocol. Larger protocols may need ~10 minutes.

---

## Step 7 — Dedup, aggregate, output

1. Group findings by `(canonical_vulnerability_type, affected_file, affected_function)`. Two findings with the same triple are duplicates.
2. The highest-severity finding wins each cluster's representative slot.
3. Output a single JSON object matching the schema below. By default, no prose around it, no markdown fences. (If the user explicitly asked for a Markdown report, render the same content as a Markdown report — see the Markdown variant at the bottom.)

```json
{
  "scanner": "drozer-lite",
  "version": "0.3.0",
  "profiles_used": ["universal", "reentrancy", "oracle"],
  "files_analyzed": [
    "KHYPE.sol", "StakingManager.sol", "StakingAccountant.sol",
    "ValidatorManager.sol", "PauserRegistry.sol",
    "OracleManager.sol", "oracles/DefaultAdapter.sol",
    "oracles/DefaultOracle.sol", "oracles/IOracleAdapter.sol"
  ],
  "clusters": [
    {"name": "StakingCluster", "files": 3, "findings": 6},
    {"name": "ControlCluster", "files": 2, "findings": 2},
    {"name": "OracleCluster", "files": 4, "findings": 3}
  ],
  "findings": [
    {
      "vulnerability_type": "lifecycle_state_residue",
      "affected_function": "confirmWithdrawal",
      "affected_file": "StakingManager.sol",
      "severity": "HIGH",
      "explanation": "confirmWithdrawal requires `address(this).balance >= amount` but the receive() fallback at L208 unconditionally calls stake(). Any HYPE sent to the contract is auto-staked instead of accumulating in contract balance, so withdrawals can never be confirmed.",
      "line_hint": 305,
      "confidence": "HIGH",
      "source_profile": "universal",
      "cluster": "StakingCluster",
      "cross_cluster": false,
      "swc_id": null,
      "cwe_id": "CWE-672"
    }
  ],
  "stats": {
    "wall_time_sec": 1247,
    "clusters_analyzed": 3,
    "checks_loaded": 105,
    "dedup_clusters_merged": 2,
    "dedup_total": 13,
    "dedup_representatives": 11
  },
  "warnings": []
}
```

### Field rules

- `scanner` is always `"drozer-lite"`.
- `version` is `"0.3.0"`.
- `vulnerability_type` MUST be a snake_case canonical tag from the vocabulary at the bottom of this file. If genuinely none fit, fall back to a short snake_case description.
- `severity` is exactly one of `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`. Uppercase.
- `confidence` is exactly one of `HIGH`, `MEDIUM`, `LOW`. Uppercase.
- `source_profile` MUST be one of the profiles you loaded in Step 3.
- `cluster` MUST be one of the cluster names from Step 4.
- `cross_cluster` is `true` if the finding was discovered in Step 6 (cross-cluster sweep), `false` otherwise.
- `swc_id` / `cwe_id` are nullable. Set them when the canonical vocabulary entry has them.
- `findings` may be empty.
- `warnings` should hold any size warnings, profile-load issues, or skipped clusters.

---

## Step 8 — Honest framing

ALWAYS end your response (after the JSON or Markdown report) with this disclaimer, verbatim. Do not soften it. Do not skip it.

> drozer-lite is a pattern-level scanner with cross-file awareness. It catches bugs from a curated checklist of 180 patterns across 13 protocol-type profiles, all derived from real audit findings. It does NOT do multi-step actor reasoning, chain-composition analysis, or formal verification. A clean drozer-lite run is NOT a clean audit. For high-value contracts, use `/droz3r` (the full drozer pipeline) or a human auditor on top of this.

Then add a one-line time disclosure:

> Total wall-clock time: ~XX min. {N} clusters analyzed across {M} files. {K} profiles loaded.

---

## Canonical vulnerability vocabulary (use these as `vulnerability_type`)

These are the snake_case tags. Each tag has a fixed meaning and an optional SWC/CWE cross-reference. If a finding genuinely matches none, use a short snake_case fallback and accept it will not be canonicalized.

### Reentrancy / external call ordering
- `reentrancy` — External call before state update; re-entrant caller drains balance. (SWC-107, CWE-841)
- `cross_function_reentrancy` — State changed in one function is read inconsistently in another via callback. (SWC-107)
- `callback_hook_reentrancy` — ERC777/721/1155 receiver hook reenters before state finalization. (SWC-107)

### Access control
- `missing_access_control` — State-changing function lacks an authorization check. (SWC-105, CWE-284)
- `tx_origin_auth` — Authorization decision uses tx.origin instead of msg.sender. (SWC-115)
- `privilege_retention_after_transfer` — Deployer or prior owner retains non-owner roles after ownership transfer.
- `rate_limit_bypass` — Sibling function or alternative path bypasses an enforced rate limit.

### Math / arithmetic
- `integer_overflow` — Arithmetic overflow or underflow that wraps. (SWC-101, CWE-190)
- `unsafe_cast_truncation` — Narrowing cast (e.g. uint256→uint160) truncates a critical value.
- `decimal_scaling_mismatch` — Heterogeneous decimal scaling in accumulator math.
- `formula_parameter_transposition` — Formula parameters swapped (e.g. eloA/eloB) producing inverted results.
- `division_by_zero` — Denominator can reach zero in a value-moving operation.

### Token / approval
- `unchecked_return_value` — External call return value not verified. (SWC-104, CWE-252)
- `non_standard_erc20` — Non-standard ERC20 (e.g. USDT) returns no bool — call appears to succeed silently.
- `max_allowance_drain` — Approval to type(uint).max enables cross-contract drain by intermediate.
- `low_level_call_silent_success` — Low-level call to non-existent address returns success without code-size guard.

### Signatures
- `signature_replay` — Signed message can be replayed across chains, contexts, or sessions. (SWC-121)
- `permit_frontrun` — Public permit() can be front-run to consume the user's signature without try/catch.
- `eip712_typehash_mismatch` — EIP-712 type hash differs from on-chain encoding; signatures never validate.
- `signature_authorization_gap` — Signature is valid but the signer is not authorized for the target account.
- `unchecked_signed_field` — Signed struct field is included in the signature but never enforced on-chain.

### Oracles
- `oracle_staleness` — Oracle data freshness is not validated before use.
- `oracle_manipulation` — On-chain price source can be manipulated within a single transaction.
- `oracle_failure_cascading` — Oracle failure (zero / max return) cascades into sell-at-zero or DoS.

### Vault / shares
- `share_inflation` — ERC4626 share inflation via first-depositor rounding or donation attack.
- `lifecycle_state_residue` — State remains active after lifecycle transition.
- `missing_slippage_protection` — Trade or LP function lacks min-out / deadline protection.

### Cross-chain
- `cross_chain_replay` — Cross-chain message can be replayed across chains or peers.
- `missing_destination_check` — Receiver does not verify it is the intended chain/destination of the payload.
- `cross_chain_address_substitution` — msg.sender reused as a destination-chain identity (incompatible across chains).
- `msgvalue_unsigned` — msg.value not bound by the signature, allowing executor injection.

### Storage / proxy
- `uninitialized_proxy` — Logic contract initializer not disabled. (SWC-118)
- `storage_layout_collision` — Upgradeable contract storage layout changed without preserving slots. (SWC-124)
- `uninitialized_storage` — Storage variable defaults to zero and an unset state passes guards. (SWC-109)

### Other
- `delegatecall_to_untrusted` — delegatecall target is attacker-controllable. (SWC-112)
- `timestamp_dependence` — Critical logic depends on block.timestamp in a manipulable way. (SWC-116)
- `missing_event_emission` — State-changing operation does not emit a corresponding event.
- `front_running` — Same-block front-running enables ordering-dependent profit. (SWC-114)
- `vrf_callback_gas` — VRF fulfillment callback exceeds the configured gas limit and reverts.
- `dust_order_dos` — Residual-below-threshold orders block price levels and DoS the book.
- `pause_time_accumulation` — Time-dependent state continues to accumulate while the protocol is paused.
- `unbounded_loop` — Loop over user-pushable collection with no upper bound.
- `irreversible_admin_action` — Admin parameter change with no timelock or two-step apply.

---

## Markdown variant (only if the user asks)

If the user explicitly requests a Markdown report, format like this:

```markdown
# drozer-lite report

**Profiles**: universal, reentrancy, oracle
**Files analyzed** (9): KHYPE.sol, StakingManager.sol, ...
**Clusters**: 3 (StakingCluster, ControlCluster, OracleCluster)

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0     |
| HIGH     | 1     |
| MEDIUM   | 3     |
| LOW      | 5     |
| INFO     | 2     |

## Findings

### 1. `lifecycle_state_residue` — HIGH (cross-cluster: false)
**Function**: `confirmWithdrawal`
**File**: `StakingManager.sol:L305`
**Cluster**: `StakingCluster`
**Profile**: `universal` · **Confidence**: HIGH · CWE-672

confirmWithdrawal requires `address(this).balance >= amount` but the receive() fallback ...
```

Then the disclaimer.

---

## Hard rules

1. **Do not** read checklists for profiles you did not load in Step 3.
2. **Do not** invent vulnerability types absent from the canonical vocabulary unless nothing fits.
3. **Do not** report findings without a specific function and file location.
4. **Do not** skip the honest framing disclaimer.
5. **Do not** soften severity ratings to be polite. Use the matrix.
6. **Do not** call any tool other than Read / Glob to gather source. There is no LLM API key in this skill — you ARE the LLM.
7. **Do not** auto-select `icp` or `solana` profiles. They are explicit-only.
8. **Do not** exceed the 1MB total source budget. Refuse politely and recommend `/droz3r`.
9. **Do not** skip Step 6 (cross-cluster sweep) — it is the difference between v0.3.0 and v0.2.x.
10. **Do not** load a profile checklist for every cluster — load each profile checklist ONCE at the start of analysis and reuse it across clusters.
11. **Do not** reveal the inventory map or the cluster plan unless the user asks. They are working artifacts, not output.

---

## Time and cost expectations

| Protocol size              | Files | Clusters | Wall-clock | Notes                                |
|----------------------------|-------|----------|------------|--------------------------------------|
| Single contract (≤30KB)    | 1     | 1        | 3-5 min    | Very small, no Step 6 work needed    |
| Small protocol (≤100KB)    | 2-10  | 2-3      | 10-20 min  | Kinetiq-sized                        |
| Medium protocol (≤300KB)   | 10-30 | 4-8      | 25-45 min  | Aave-V3-core-sized                   |
| Large protocol (≤500KB)    | 30-60 | 8-15     | 45-75 min  | Compound-V3-sized                    |
| Very large (>500KB)        | 60+   | 15+      | 75-120 min | Soft warning, recommend /droz3r      |
| Refusal threshold (>1MB)   | —     | —        | refuse     | Hard stop, recommend /droz3r         |

These are wall-clock estimates inside a Claude Code session. Cost is zero marginal — drozer-lite uses the same model context the user is already paying for.

drozer-lite is a coffee-break tool, not an instant tool. That trade is what makes it actually useful for real protocols instead of pedagogical toys.
