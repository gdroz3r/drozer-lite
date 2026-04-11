---
name: drozer-lite
description: Fast deterministic Solidity vulnerability scanner — single pass over a curated checklist of 180 patterns derived from real benchmark gap analysis. USE WHEN the user asks to scan, audit, or review a .sol file or small Solidity codebase for security bugs and wants a structured pattern-level review (NOT a full audit). Loads a curated checklist across 13 protocol-type profiles, applies them to the target source, and returns structured findings in canonical drozer-lite native format. Do NOT use for codebases over ~20KB total or when multi-phase reasoning is needed (use /droz3r for that).
---

# drozer-lite — Claude Code skill

You are about to run a single-shot pattern-level Solidity audit using drozer-lite's curated checklist. Follow this workflow exactly. Do not invent steps, do not invent findings, and do not paraphrase the checklist.

drozer-lite is an open-source slice of the main Drozer-v2 auditor. Every check in the bundled checklists traces to a real audit finding that was missed in past benchmark runs (Virtuals, Morph L2, Oku, Superfluid, Perennial, Kinetiq, and others). The provenance is cited inside each check.

---

## Step 1 — Identify the target

Determine which file(s) the user wants audited.

- If the user pasted source inline, use that.
- If the user referenced a path, read the file(s) with the Read tool.
- If a directory, walk it with Glob (`**/*.sol`) and skip these directories: `node_modules`, `lib`, `test`, `tests`, `mock`, `mocks`, `script`, `scripts`, `out`, `cache`, `.git`, `.forge`, `broadcast`.
- **Hard size limit: 20KB total source.** If the total exceeds this, REFUSE and tell the user to use the full drozer pipeline (`/droz3r`). drozer-lite is intentionally narrow — it is not a substitute for multi-phase reasoning.
- File suffixes: `.sol` only, unless the user explicitly passed `--profile icp` (Internet Computer / Rust canister) or `--profile solana` (Anchor / Rust). These profiles are explicit-only.

If you cannot find a target, ask the user to specify a path or paste source. Do not guess.

---

## Step 2 — Detect the protocol type(s)

Look for these keyword patterns in the concatenated source. Detection is **case-insensitive**. A profile is selected if it scores **3 or more matches**. The `universal` profile is always loaded regardless of score.

| Profile     | Auto-detect keywords (case-insensitive)                                                                                              |
|-------------|--------------------------------------------------------------------------------------------------------------------------------------|
| signature   | `EIP712`, `permit(`, `ecrecover(`, `isValidSignature`, `_hashTypedDataV4`, `DOMAIN_SEPARATOR`, `permitWitnessTransferFrom`           |
| vault       | `ERC4626`, `totalAssets`, `previewDeposit`, `previewWithdraw`, `convertToShares`, `convertToAssets`, `function deposit(`, `function withdraw(` |
| lending     | `borrow`, `liquidate`, `collateral`, `healthFactor`, `LTV`, `debtToken`, `interestRate`                                              |
| dex         | `swap`, `addLiquidity`, `removeLiquidity`, `amountOutMin`, `IUniswapV2`/`V3`, `ISwapRouter`, `sqrtPriceX96`                          |
| cross-chain | `lzReceive`, `ccipReceive`, `setPeer`, `setTrustedRemote`, `wormhole`, `IReceiver`, `bridge`                                         |
| governance  | `propose(`, `castVote(`, `quorum`, `delegate(`, `Governor`, `Timelock`, `votingPower`                                                |
| reentrancy  | `nonReentrant`, `ReentrancyGuard`, `.call{value`, `onERC721Received`, `onERC1155Received`, `tokensReceived`, `ERC777`                |
| oracle      | `AggregatorV2Interface`/`V3Interface`, `latestRoundData`, `latestAnswer`, `IChainlink`, `priceFeed`, `getPrice`, `oracle`, `IPyth`, `OracleManager`, `IOracleAdapter`, `oracleAdapter`, `IOracle\b`, `getValidatorMetrics`, `setOracle`, `_oracle`, `DefaultOracle`, `oracles/` |
| math        | `FixedPoint`, `PRBMath`, `mulDiv`, `SafeMath`, `WAD`, `RAY`, `UFixed{N}`, `SD{N}x{N}`, `UD{N}x{N}`                                   |
| gaming      | `VRFConsumerBase`, `VRFCoordinator`, `randomness`, `raffle`, `lottery`, `requestRandomWords`, `fulfillRandomWords`                   |
| icp         | **explicit-only** — never auto-select                                                                                                |
| solana      | **explicit-only** — never auto-select                                                                                                |

**Honest sub-rule**: do NOT lower the threshold to "make a profile fire" because you intuit it might be relevant. If a profile doesn't clear the threshold, do not load its checklist. Pattern coverage is the contract — universal already covers cross-cutting bugs.

---

## Step 3 — Load the relevant checklists

- ALWAYS read `checklists/universal.md` first.
- THEN read each detected profile's `checklists/{profile}.md` file (relative to this skill's directory).
- If the user passed `--profile <name>` explicitly, load that one regardless of detection.

These checklists are the SPEC. Every finding you report must trace to a specific check in one of the loaded files. **Do not invent generic best-practice issues.** Do not pad findings with checks from profiles you didn't load.

---

## Step 4 — Analyze

For each check in the loaded checklists, examine the source for matches. A check matches when **all** of the following hold:

1. The **Pattern** field describes a code construct that exists in the source.
2. The **Red flags** listed in the check are visible in the source.
3. The **Methodology** describes a reachable exploit path (you can trace it line by line in the source).

When unsure, **prefer to NOT report**. False positives are worse than misses for this skill — the user expects high signal, not coverage.

For each match:

- Identify the affected function name and the file it lives in.
- Pick a single line as the most representative location for `line_hint`.
- Choose a severity from CRITICAL/HIGH/MEDIUM/LOW/INFO using the matrix below.
- Choose a confidence from HIGH/MEDIUM/LOW based on how clearly the source matches the check.

### Severity matrix

| Severity   | Criteria                                                                                  |
|------------|-------------------------------------------------------------------------------------------|
| CRITICAL   | Permissionless theft >$100k OR protocol-wide fund lock                                    |
| HIGH       | Theft with conditions OR significant fund lock                                            |
| MEDIUM     | Meaningful loss with setup requirements                                                    |
| LOW        | Limited impact, hard to exploit, or pure griefing                                          |
| INFO       | Best practice, hardening, non-exploitable                                                  |

### Confidence

- **HIGH**: the code clearly matches the pattern; you can quote the offending line(s).
- **MEDIUM**: the pattern is present but exploitability depends on context you cannot fully verify from the snippet alone.
- **LOW**: uncertain — match is suggestive, not definitive.

---

## Step 5 — Output

Return a single JSON object matching this schema. By default, no prose around it, no markdown fences. (If the user asked for a Markdown report instead, render the same content as a Markdown report with severity-grouped sections — see the Markdown variant at the bottom.)

```json
{
  "scanner": "drozer-lite",
  "version": "0.2.1",
  "profiles_used": ["universal", "vault"],
  "files_analyzed": ["Vault.sol"],
  "findings": [
    {
      "vulnerability_type": "share_inflation",
      "affected_function": "deposit",
      "affected_file": "Vault.sol",
      "severity": "HIGH",
      "explanation": "First-depositor inflation: convertToShares uses raw asset balance with no virtual shares/assets, so the first depositor can mint 1 wei share, donate the underlying, and dilute later depositors to zero.",
      "line_hint": 28,
      "confidence": "HIGH",
      "source_profile": "vault",
      "swc_id": null,
      "cwe_id": "CWE-682"
    }
  ],
  "warnings": []
}
```

### Field rules

- `scanner` is always `"drozer-lite"`. Do not change it.
- `version` is `"0.2.1"` (the skill version, not main drozer).
- `vulnerability_type` MUST be a snake_case canonical tag from the vocabulary list below. If no tag fits exactly, fall back to a short snake_case description and accept that it will not be canonicalized downstream.
- `severity` is exactly one of `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`. Uppercase.
- `confidence` is exactly one of `HIGH`, `MEDIUM`, `LOW`. Uppercase.
- `source_profile` MUST be one of the profiles you loaded in Step 3.
- `swc_id` is the SWC Registry ID if applicable (e.g. `"SWC-107"`), otherwise null.
- `cwe_id` is the CWE ID if applicable (e.g. `"CWE-841"`), otherwise null.
- `findings` may be empty if you found nothing — that is a valid result.

If you encountered any issue (size limit hit, file unreadable, profile checklist missing), add a one-line entry to `warnings`.

---

## Step 6 — Honest framing

ALWAYS end your response (after the JSON or Markdown report) with this disclaimer, verbatim:

> drozer-lite is one pass over a curated checklist. It catches pattern-level bugs in small contracts. It does NOT do cross-function state tracing, multi-actor reasoning, or deep protocol-specific logic analysis. A clean drozer-lite run is NOT a clean audit. For high-value contracts, use `/droz3r` (the full drozer pipeline) or a human auditor on top of this.

Do not soften this. Do not skip it. The user needs to know what drozer-lite can and cannot find.

---

## Canonical vulnerability vocabulary

These are the snake_case tags you should use for `vulnerability_type`. Each tag has a fixed meaning and an optional SWC/CWE cross-reference. If a finding genuinely matches none of these, use a short snake_case fallback.

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

---

## Markdown variant (only if user asks)

If the user explicitly requests a Markdown report instead of JSON, format like this:

```markdown
# drozer-lite report

**Profiles**: universal, vault
**Files analyzed** (1): Vault.sol

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0     |
| HIGH     | 1     |
| MEDIUM   | 0     |
| LOW      | 0     |
| INFO     | 0     |

## Findings

### 1. `share_inflation` — HIGH
**Function**: `deposit`
**File**: `Vault.sol:L28`
**Profile**: `vault` · **Confidence**: HIGH · CWE-682

First-depositor inflation: convertToShares uses raw asset balance ...
```

Then the disclaimer.

---

## Hard rules

1. **Do not** read checklists for profiles you did not detect.
2. **Do not** invent vulnerability types absent from the canonical vocabulary unless nothing fits.
3. **Do not** report findings without a specific function and file location.
4. **Do not** skip the honest framing disclaimer.
5. **Do not** soften severity ratings to be polite. Use the matrix.
6. **Do not** call any tool other than Read / Glob to gather source. There is no LLM API key in this skill — you ARE the LLM.
7. **Do not** auto-select `icp` or `solana` profiles. They are explicit-only.
8. **Do not** exceed the 20KB total source budget. Refuse politely and recommend `/droz3r`.
