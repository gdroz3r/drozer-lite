---
name: drozer-lite
description: General-purpose pattern-level smart contract vulnerability scanner with cross-file awareness. Walks any smart contract project (Solidity, Rust/Anchor/CosmWasm/IC, Move, Cairo, Vyper — single file or multi-file), builds an inventory, clusters related modules, applies a curated checklist of 180+ vulnerability patterns derived from real benchmark gap analysis across 13+ protocol-type profiles, and returns structured findings. USE WHEN the user asks to scan, audit, or review smart contract source for security bugs and wants pattern-level coverage. Designed for protocols up to ~500KB / 100 files. Wall-clock 5-30 min depending on size. Does NOT do multi-step actor reasoning, chain analysis, or formal verification — for that, use the full drozer pipeline (`/droz3r`).
---

# drozer-lite — open-source pattern-level smart contract auditor (v0.5.6, alias canonicalization only; worksheet back to v0.5.4 baseline)

You are about to run a multi-file pattern-level smart contract audit using drozer-lite's curated checklist. Follow this 8-step workflow exactly. Do not invent steps, do not paraphrase the checklist, do not invent findings.

drozer-lite is the open-source pattern-level slice of the main Drozer-v2 auditor. Every check in the bundled checklists traces to a real audit finding that was missed in past benchmark runs. The provenance is cited inside each check.

drozer-lite is intentionally narrow:

- **Pattern-level checks** drawn from a curated checklist — ~88 checks are language-agnostic, ~10 are Solidity-specific
- **Multi-language** — Solidity, Rust (Anchor, CosmWasm, IC canisters), Move (Aptos, Sui, Initia), Cairo (StarkNet), Vyper
- **Cross-file aware** (catches bugs spanning multiple contracts/modules)
- Does NOT do multi-step actor reasoning, chain composition analysis, or formal verification — that's `/droz3r` territory

The trade-off is on purpose: drozer-lite finds the bugs pattern matching CAN find, fast and reproducibly, without pretending to be a full audit pipeline.

---

## Step 1 — Identify the target and detect language

Determine which file(s) the user wants audited.

- If the user pasted source inline, treat it as a one-file target. Detect language from syntax.
- If the user referenced a path, walk it.

### Language detection (auto, from file extensions)

| Extension(s) | Language | Glob pattern | Also filter out |
|---|---|---|---|
| `.sol` | Solidity | `**/*.sol` | `node_modules`, `lib`, `forge-std`, `.forge` |
| `.rs` | Rust (Anchor / CosmWasm / IC) | `**/*.rs` | `target/`, `.cargo/`, `test_*.rs`, `*_test.rs` |
| `.move` | Move (Aptos / Sui / Initia) | `**/*.move` | `build/`, `.aptos/`, `tests/` |
| `.cairo` | Cairo (StarkNet) | `**/*.cairo` | `target/`, `tests/` |
| `.vy` | Vyper | `**/*.vy` | `tests/` |

Always filter out: `test`, `tests`, `mock`, `mocks`, `script`, `scripts`, `out`, `cache`, `.git`, `coverage`, `broadcast`, `node_modules`.

If a project has mixed languages (e.g. `.sol` + `.rs`), detect the PRIMARY language by file count / byte weight and note the secondary. Load profiles for the primary language; if a secondary language has significant source (>20% by bytes), load its profiles too.

- **Soft warning**: if total source > 500KB, tell the user "this will take ~30+ minutes" and continue.
- **Hard refusal**: if total source > 1MB, REFUSE. Recommend `/droz3r` (the full drozer pipeline).

If you cannot find any source, ask the user to specify a path or paste source. Do not guess.

### Language determines what "function", "modifier", "state variable" mean in Steps 2-6

| Concept | Solidity | Rust (Anchor/CosmWasm) | Move | Cairo |
|---|---|---|---|---|
| Public function | `external`/`public` | `pub fn`, `#[msg(execute)]`, `#[instruction]` | `public entry fun`, `public fun` | `#[external(v0)]`, `fn` in impl |
| Access control | `onlyOwner`, `onlyRole(R)` modifier | `require!(ctx.accounts.authority == ...)`, `#[access_control]` | `assert!(signer::address_of(s) == @admin)` | `assert(caller == owner)` |
| State variable | contract-level storage | `Account<'info, T>`, `#[account]` struct fields | `borrow_global<T>`, resource struct fields | `@storage_var` |
| External call | `.call`, `interface(addr).fn()` | CPI (`invoke`, `invoke_signed`), `CosmosMsg` | `coin::transfer`, module call | syscall, contract call |
| Reentrancy guard | `nonReentrant`, `ReentrancyGuard` | manual flag, `#[non_reentrant]` in some frameworks | N/A (Move is not reentrant by design) | N/A (Cairo is not reentrant by design) |
| Import/dependency | `import`, `using...for` | `use`, `mod`, Cargo.toml deps | `use`, `friend` | `use`, imports |

When applying checks from `.claude/skills/drozer-lite/checklists/universal.md`, **translate the Solidity-phrased red flags to the target language's equivalent**. The METHODOLOGY is language-agnostic; only the SYNTAX differs. For example:
- UNI-1 says "Missing `onlyOwner`/`onlyRole(...)` on state-changing function" → in Rust, check for missing `require!(authority == ...)` or `#[access_control(...)]`
- UNI-3 says "Balance/ownership update AFTER `.call` or token transfer" → in Rust, check for CPI invocations before account state updates

---

## Step 2 — Build the inventory (cheap structural pass)

Read each in-scope file with the Read tool. Do NOT analyze code yet — only extract structure. Build an in-context inventory map covering:

For each file:
- **Path** and approximate byte size + line count
- **Modules / contracts / programs** declared (and what they extend / implement)
- **Public / external function signatures** (name + params + visibility + guards, no body). Use the language's convention from the Step 1 table.
- **State variables / account structs / storage vars** (name + type + visibility)
- **Access control mechanisms** (modifiers, assert-based guards, access_control attributes)
- **External calls visible**: cross-contract calls, CPI, module calls, system calls, delegate calls
- **Imports / dependencies** (which other in-scope files this file depends on)

Format the inventory like this (keep it terse — this is your context_map for cross-file detection):

Format: `File.sol (XKB, YL) → Contracts: Name → Parent; External fns: ...; State: ...; External calls: ...; Imports: ...`

Use real file/contract names from the source. Keep it terse — this is your context_map for cross-file detection in Step 5.

---

## Step 3 — Detect profiles (with always-load fallback)

Apply the keyword detection table below to the WHOLE inventory (not file-by-file). Detection is **case-insensitive**. A profile is **auto-loaded** if it scores **3 or more distinct keyword matches** across the inventory.

**ALWAYS LOAD**: `universal` (regardless of detection)

**Auto-detect** (per-profile threshold = 3 distinct keyword matches). Keywords below are **common-pattern names** and regex fragments that appear across the entire Solidity ecosystem — they must never encode benchmark-specific identifiers. When applying detection, treat each row as a set of case-insensitive regex patterns. Some patterns use `\w*` deliberately to tolerate real-world naming (prefixed function names like `depositFoo`, suffixed variants like `previewDepositVault`, protocol-specific wrappers like `swapXForY`). A keyword match should accept the pattern followed by typical word characters.

| Profile | Keywords and regex fragments (case-insensitive) |
|---|---|
| signature   | `EIP712`, `permit\s*\(`, `ecrecover\s*\(`, `isValidSignature`, `_hashTypedDataV4`, `DOMAIN_SEPARATOR`, `permitWitnessTransferFrom`, `_signTypedData`, `Permit2`, `IERC1271`, `\w*Permit\w*\s*\(`, `SignatureLib`, `recoverSigner`, `signedHash` |
| vault       | `ERC4626`, `totalAssets`, `previewDeposit\w*`, `previewWithdraw\w*`, `previewRedeem\w*`, `convertToShares`, `convertToAssets`, `function\s+\w*[Dd]eposit\w*\s*\(`, `function\s+\w*[Ww]ithdraw\w*\s*\(`, `function\s+\w*[Rr]edeem\w*\s*\(`, `IERC4626`, `sharesOf`, `maxDeposit`, `\w*Vault\w*`, `lvToken`, `vToken` |
| lending     | `\w*[Bb]orrow\w*`, `\w*[Ll]iquidate\w*`, `collateral`, `healthFactor`, `\bLTV\b`, `debtToken`, `interestRate`, `\w*[Rr]epay\w*`, `function\s+\w*[Ss]upply\w*\s*\(`, `IPool`, `ILendingPool`, `_borrow`, `cToken`, `underlying` |
| dex         | `\w*[Ss]wap\w*\s*\(`, `addLiquidity\w*`, `removeLiquidity\w*`, `amountOutMin`, `amountInMax`, `\bUniswapV[234]\b`, `IUniswapV[234]`, `ISwapRouter`, `sqrtPriceX96`, `getAmountsOut`, `getAmountOut`, `\bRouter0[1-4]\b`, `createPair\s*\(`, `MinimalUniswapV2Library`, `_pair` |
| cross-chain | `lzReceive`, `ccipReceive`, `setPeer`, `setTrustedRemote`, `wormhole`, `IReceiver`, `\w*[Bb]ridge\w*\s*\(`, `ILayerZero`, `NonblockingLzApp`, `_nonblockingLzReceive`, `IRouterClient`, `crossChain\w*`, `CCIPSender`, `HyperlaneRouter` |
| governance  | `propose\s*\(`, `castVote\w*\s*\(`, `quorum`, `delegate\w*\s*\(`, `Governor`, `Timelock`, `votingPower`, `IGovernor`, `_execute\s*\(`, `getVotes`, `IVotes`, `proposalThreshold`, `voteStart`, `voteEnd` |
| reentrancy  | `nonReentrant`, `ReentrancyGuard`, `\w*[Rr]eentranc\w*`, `\.call\s*\{\s*value`, `\.call\s*\(`, `onERC721Received`, `onERC1155Received`, `tokensReceived`, `ERC777`, `IERC777Recipient`, `_checkOnERC721Received`, `IERC1155Receiver`, `\bMutex\w*`, `NoReentrant`, `\bLock\w*\.acquire`, `locked\s*=\s*true`, `_status\s*=\s*1` |
| oracle      | `AggregatorV[23]Interface`, `latestRoundData`, `latestAnswer`, `IChainlink`, `priceFeed`, `\w*[Gg]etPrice\w*`, `\boracle\w*`, `\w*Oracle\w*`, `IPyth`, `IOracle\w*`, `oracleAdapter`, `IOracleAdapter`, `setOracle\w*`, `_oracle`, `\boracles/`, `IRates`, `exchangeRate\s*\(` |
| math        | `FixedPoint`, `PRBMath`, `mulDiv`, `SafeMath`, `\bWAD\b`, `\bRAY\b`, `UFixed\w*`, `SD\d+x\d+`, `UD\d+x\d+`, `abdk`, `FullMath`, `MathUpgradeable`, `MathHelper`, `UQ\d+x\d+`, `\bsqrt\s*\(` |
| gaming      | `VRFConsumerBase`, `VRFCoordinator`, `randomness`, `\w*[Rr]affle\w*`, `\w*[Ll]ottery\w*`, `requestRandomWords`, `fulfillRandomWords`, `ChainlinkVRF`, `VRFV2`, `IVRFCoordinator`, `commitReveal`, `randaoMix` |
| stableswap  | `StableSwap`, `\bamp\b`, `amplification`, `compute_d`, `compute_y`, `\bnewton\b`, `invariant.*D`, `stableswap_y`, `n_coins.*ann`, `D_prod`, `amp_factor` |

### Language-specific profiles (auto-load by detected language)

When the detected language is NOT Solidity, auto-load the corresponding language profile:

| Detected language | Auto-load profile | Condition |
|---|---|---|
| Rust + Anchor patterns (`declare_id!`, `#[program]`, `#[account]`) | `solana` | Score ≥ 2 Anchor keywords |
| Rust + IC patterns (`ic_cdk`, `#[update]`, `#[query]`, `candid`) | `icp` | Score ≥ 2 IC keywords |
| Rust + CosmWasm patterns (`cosmwasm_std`, `#[entry_point]`, `ExecuteMsg`) | load `universal` only (no dedicated CosmWasm profile yet) | — |
| Move | load `universal` only (no dedicated Move profile yet) | — |
| Cairo | load `universal` only (no dedicated Cairo profile yet) | — |
| Vyper | load `universal` + any Solidity profiles that fire (Vyper shares EVM patterns) | — |

`icp` and `solana` profiles are NO LONGER explicit-only. They auto-load when the language detection identifies Anchor or IC canister Rust code. They can still be forced via `--profile` when auto-detection misses.

**Hard rule**: do not lower the threshold to "make a profile fire" because you intuit it might be relevant. If a profile genuinely does not clear the threshold, do not load its checklist. Pattern coverage IS the contract.

**Document the selection**. Output a "Profile Selection" block the user can read, listing every profile and its match count:

```
PROFILE SELECTION (synthetic example):
  universal     → ALWAYS LOADED
  reentrancy    → AUTO-LOADED (4 matches: nonReentrant, ReentrancyGuard, .call{value, onERC721Received)
  oracle        → AUTO-LOADED (3 matches: priceFeed, IOracle, exchangeRate())
  vault         → not loaded (1 match: ERC4626)
  lending       → not loaded (0 matches)
  signature     → not loaded (1 match: permit()-shaped library call)
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
CLUSTER PLAN (synthetic example):
  Cluster 1 — PrimaryCluster (54KB, 1.4K lines)
    Files: Token.sol, Service.sol, Accountant.sol
    Dependencies: Token imports IPauseRegistry; Service imports Token + IAccountant; Accountant imports IRegistry
  Cluster 2 — ControlCluster (24KB, 643 lines)
    Files: Registry.sol, PauseRegistry.sol
    Dependencies: Registry imports IPauseRegistry + IService
  Cluster 3 — OracleCluster (21KB, 542 lines)
    Files: OracleAggregator.sol, adapters/Adapter.sol, adapters/SourceImpl.sol, adapters/IAdapter.sol
    Dependencies: OracleAggregator imports IAdapter; Adapter imports IAdapter
```

---

## Step 5 — Per-cluster analysis

For each cluster:

1. **Read the cluster's source — EVERY LINE, NO EXCEPTIONS.** Read each file in the cluster fully. If a file exceeds ~40KB (~500 lines), read it in sequential chunks using offset+limit (e.g. offset=0 limit=500, then offset=500 limit=500, etc.) until the entire file is read. Do NOT skip, sample, or "read the important parts." Every line of in-scope source must be read. Partial source reading is the #1 cause of missed findings — a 25% read produces 25% recall. This is non-negotiable.
2. **Read the relevant checklists** — Read `.claude/skills/drozer-lite/checklists/universal.md` always, plus each auto-loaded profile checklist (`.claude/skills/drozer-lite/checklists/{profile}.md`). These paths are relative to the project root (current working directory) where the skill is invoked.
3. **Reference the inventory from Step 2** — for cross-cluster bug detection. When the cluster you're analyzing calls a function in another cluster, look up the target's signature in the inventory; you don't need to re-read the other cluster's full source.
4. **Apply each loaded check** — for each check in the loaded checklists, examine the cluster source. **If the target language is not Solidity, translate the check's Solidity-phrased red flags to the equivalent in the target language** using the concept-mapping table from Step 1. The METHODOLOGY is language-agnostic; only the SYNTAX differs. A check matches when ALL of:
   - The **Pattern** field describes a code construct that exists in the cluster source (in the target language's idiom)
   - The **Red flags** (or their language-translated equivalents) are visible in the source
   - The **Methodology** describes a reachable exploit path you can trace line by line
4a. **Textbook-pattern specific-break requirement** (new in v0.5.1). For canonical well-known patterns — **reentrancy / CEI**, **signature replay**, **reward-debt / MasterChef-style accumulator**, **multisig stale-approval after owner removal**, **ERC4626 first-depositor inflation**, **flash loan oracle manipulation**, **approve-then-transferFrom race** — pattern presence is NOT sufficient. The finding MUST identify the **specific line** in the current code that deviates from the textbook safe version. Competent authors handle these patterns correctly most of the time; emitting on pattern presence without a concrete break is the top precision failure on complex clean contracts.

   - Good: *"Line 65 calls `msg.sender.call{value: excess}('')` BEFORE line 68 updates `tokensSold`. Textbook safe version updates state before the external call."*
   - Bad: *"The reward-debt pattern is present; a user acquiring LP after fees accrue can claim retroactively."* (class description, not a code-level break)
   - Bad: *"removeOwner does not clear approvals — classic multisig bug."* (class description; requires you to actually show that the approvals are counted AFTER removal in the current execute() path, with specific lines)

5. **When unsure, do NOT report.** This is a hard rule, not a preference. False positives are worse than misses.

   (a) **Hedging by hypothetical future state** — banned. Do NOT report any finding whose body is "what if an admin whitelists a malicious token…", "if a future upgrade adds…", "if ERC777 is ever added…", "if the oracle returns zero…" unless the codebase ALREADY contains evidence that the hypothetical condition holds (e.g., ERC777 is actually in scope, the oracle is actually unvalidated in the read path).

   (b) **Hedging by admin cooperation** — banned (new in v0.5.1). Do NOT report any finding whose exploit sentence requires the admin/owner/trusted actor to deliberately misconfigure parameters, set addresses to zero, or cooperate with the attacker. Examples that must be suppressed: "admin can set `sanctionsList` to zero and disable sanctions", "admin can call `setFee(10000)` and drain", "arbitrator can transfer role to attacker". These are centralization concerns, not exploits. Move them to `warnings[]` as `"centralization: <title>"` strings if the user explicitly invoked with `--include-centralization`. Never emit them in `findings[]` by default.

   Speculative hedging findings of either type are the #1 source of false positives and MUST be suppressed at the source, not at Step 7.
6. **For each match**, identify:
   - The affected function name and the file it lives in (full path within the project)
   - A specific line as the most representative location for `line_hint`
   - A severity from CRITICAL/HIGH/MEDIUM/LOW/INFO using the matrix below
   - A confidence from HIGH/MEDIUM/LOW based on how clearly the source matches the check
   - The check ID that fired (e.g. `UNI-1`, `RE-2`, `ORC-3`) — record this internally
7. **Add cluster metadata** to each finding: `cluster: "<cluster name>"`. The dedup pass will use this.
8. **Do not output yet** — accumulate findings in your working set. Output is at Step 7.

You may analyze clusters sequentially (recommended for token budget). Each cluster gets its own independent reasoning pass — but ALL clusters share the same checklist context that you loaded once at the start.

### Severity decision table

Pick severity by walking this table top-to-bottom and stopping at the first row that matches. Do NOT pick severity by "feel" — the table is the contract. Aligned with industry convention (Code4rena / Immunefi / SWC Registry).

| If the finding is… | …and the attacker is… | …and the impact is… | Severity |
|---|---|---|---|
| Direct drain / unauthorized mint / arbitrary-state-write | **permissionless** (anyone) | protocol-wide funds at risk, no preconditions | **CRITICAL** |
| Signature replay on a token-moving or authorization function | permissionless | repeated fund transfer until balance/allowance exhausted | **CRITICAL** |
| CEI violation / reentrancy that drains a pool | permissionless | full pool drain in a single tx | **CRITICAL** |
| Missing access control on a function that **sets an economic parameter** (rate, fee, price, reward, threshold) | permissionless | protocol-wide economic manipulation, indirect fund loss | **HIGH** |
| Missing access control on a function that sets **per-user** state | permissionless | a single user's state is corrupted | **MEDIUM** |
| CEI violation / reentrancy with a cap on damage (per-user, per-epoch) | permissionless | bounded fund loss | **HIGH** |
| Signature replay on a non-fund-moving function | permissionless | unbounded action replay, no direct fund loss | **MEDIUM** |
| Missing input validation that allows a permissionless caller to set a parameter to an out-of-spec value causing fund loss (e.g. `discountBps > 10000`, `fee > 100%`) | permissionless OR creator of a permissionless market | direct fund loss once the bad value is set | **HIGH** |
| Missing input validation with no direct fund loss | permissionless | griefing, DoS, or broken-state | **MEDIUM** |
| Racing a legitimate caller for funds (front-run withdrawal vs release) | permissionless | race winner takes funds that were rightfully the loser's | **MEDIUM** |
| Division by zero that bricks a critical function | permissionless | permanent DoS of stake/redeem/withdraw | **HIGH** |
| Division by zero in a view-only or non-critical path | permissionless | view call reverts, no state impact | **LOW** |
| Unchecked return value of a known-standard token (SafeERC20 not used) AND the token whitelist includes a specific non-standard token (USDT, BNB, etc.) | permissionless | silent accounting drift | **MEDIUM** |
| Unchecked return value with no identified non-standard token in scope | — | speculative | **DROP — FP risk** |
| Missing nonReentrant guard AND an actual callback-enabled token is in scope (ERC777, ERC1155 receiver hook used) | permissionless | real reentrancy path | **HIGH** |
| Missing nonReentrant guard with no callback-enabled token in scope | — | speculative | **DROP — FP risk** |
| Use of `transfer()` (2300 gas) for payouts to EOAs only | — | none | **DROP — FP risk** |
| Use of `transfer()` (2300 gas) for payouts to addresses that can be arbitrary contracts | permissionless | bricked withdrawal if recipient's fallback costs > 2300 gas | **LOW** |
| Admin action with no timelock, no multi-sig enforcement visible, and the admin controls fund movement | admin | rug pull / instantaneous parameter change | **MEDIUM** (centralization) |
| Missing event emission on state-changing function | — | off-chain indexers miss state change | **LOW** or **INFO** |
| Griefing / DoS without fund loss | permissionless | single-user DoS | **LOW** |
| Griefing / DoS affecting ALL users of a critical function | permissionless | protocol-wide DoS | **HIGH** |
| Style / best-practice / non-exploitable | — | hardening only | **INFO** |

**Adjustment rules**:

- **Cap at MEDIUM** if the attacker must already be a trusted role (admin, owner, governance-elected). This is centralization risk, not exploitation.
- **Bump one tier** if the protocol holds >$10M TVL in a similar deployed protocol. drozer-lite does not know TVL; apply this only if the user stated the context.
- **Drop the finding** if the "exploit" requires a specific off-chain setup drozer-lite cannot verify (e.g., "if the admin key is compromised by phishing").

**If the table has no row that matches**: the finding is either novel or you are describing a class of issue drozer-lite is not calibrated for. Default to **LOW** and document the mismatch in your reasoning. Do not invent a severity.

### Weak-evidence severity floor (new in v0.5.1)

If the exploit sentence's `[CONCRETE LOSS]` depends on ANY of the following, cap severity at **LOW** regardless of what the main severity table returned:

- **Off-chain tree / payload construction** — e.g., merkle-leaf reuse across windows requires the admin to reuse roots off-chain; the contract itself cannot enforce it.
- **Cross-contract configuration the admin sets later** — e.g., "if the token whitelisted via `setToken` returns false on transfer" when no such token is currently referenced in scope.
- **Unobservable user ordering or mempool races** that the contract neither enforces nor defends against, where either ordering is legitimate.
- **External callback behavior** on callee types that are not in the current whitelist (ERC777 hooks, generic ERC1155 receivers) unless the code actually integrates those standards.

Combined with the severity-tier output filter (Step 7 rule 1a), these capped-at-LOW findings move to `warnings[]` by default. This kills the class of "this could be bad if the admin / off-chain / future setup cooperates" speculations that survive Gate A by sounding concrete but depend on unobservable context.

### Confidence

- **HIGH**: code clearly matches the pattern; you can quote the offending line(s).
- **MEDIUM**: pattern is present but exploitability depends on context you cannot fully verify from the cluster alone.
- **LOW**: uncertain — match is suggestive, not definitive.

**Time budget for Step 5**: ~3-5 minutes per cluster of normal density. A 50KB cluster with all checks should be ~5 min. Skip checks that obviously don't apply (e.g., `permit_frontrun` on a contract with no signatures).

---

## Step 6 — Cross-cluster sweep

After all clusters are analyzed, look for bugs that span clusters. This is the step that catches bugs single-cluster analysis misses. Apply each of the 13 cross-cluster patterns below to every pair of clusters that have references in the inventory from Step 2. Patterns 1-6 catch **symmetric asymmetries** (same modifier applied here but not there). Patterns 7-13 catch **economic cross-cluster flows** (state drift, fill/drain asymmetry, consumer-side failures).

### Patterns 1-6 — symmetric asymmetry

1. **State write/read mismatches**: function in cluster A writes state variable V; function in cluster B reads V without re-validating preconditions. Look for staleness.
2. **Cross-contract access control gaps**: cluster A function F is guarded by role R; cluster B has a wrapper W around F that has weaker or no access control. The wrapper bypasses the guard.
3. **Auto-route fallbacks**: cluster A's contract has a `receive()` or `fallback()` that calls a state-changing function in the same or another cluster, so the contract balance is never what callers expect. Check whether ANY function in the inventory uses `address(...).balance` for an invariant the auto-routing breaks. **If found, severity MUST be at least HIGH** — this is the UNI-98 pattern (see universal.md).
4. **Service interface failure modes**: cluster A provides an interface (e.g., `IOracle`); cluster B consumes it without checking for stale, zero, or revert returns.
5. **Shared modifier inconsistency**: same bug class fires in cluster A but not B, even though both use the same modifier — flag the missing application in B.
6. **Pause-state asymmetry**: a pause flag in cluster A is checked in some functions but not in functionally-equivalent siblings in cluster B.

### Patterns 7-13 — economic cross-cluster flows

7. **Snapshot-consumption drift**: cluster A stores a value `V` computed from a time-varying rate or reference (e.g. `record.amountSnapshot = shares * currentExchangeRate`). Cluster B (or a later call in cluster A) mutates that rate via reported events (loss events, reward events, slashings, rebalances, fee adjustments). The stored snapshot is never re-evaluated at consumption time, so the user or protocol is settled at a stale value. Report as `lifecycle_state_residue` with MEDIUM+ severity. This catches the class-of-bug where multi-user queue ordering around rate-changing events creates unfairness.
8. **Aggregate fill/drain asymmetry**: cluster A has a variable `V` that a write path FILLS (e.g. `V += delta` on some inbound action); cluster B/A has a drain path that DRAINS `V` under some conditions but NOT others. Look for sequences where `V` can accumulate without being drained, and where the only drain path is conditional on caller actions that may never happen. Report as `lifecycle_state_residue` or `unbounded_loop` with MEDIUM+ severity. drozer-lite cannot construct the full exploit sequence — flag the class-of-bug so the auditor can investigate whether accumulated value can be trapped.
9. **Cross-cluster unchecked caller parameter**: cluster A function accepts a contract-address parameter (e.g. `target` / `router` / `factory` / `module`) and calls into it. Cluster B is the intended target but no validation enforces it. Role-gating the caller is necessary but NOT sufficient — the caller can still pass a malicious or wrong target. Check whether cluster A stores an authoritative target or validates the parameter against a whitelist.
10. **Cross-cluster role assumption drift**: cluster A calls cluster B function F which requires role R. Cluster A is ASSUMED to hold R but it's not enforced by cluster A's constructor or initialize. If R is revoked from A externally, A's calls revert silently or bubble. Flag as operational fragility (INFO) unless it also opens an attack path.
11. **Cross-cluster counter consistency**: cluster A and cluster B both write to a shared counter variable (e.g. a global total/supply/balance held in a third cluster). Verify that both writers are mutually aware or the counter would drift under concurrent access.
12. **Provider-consumer type mismatch**: cluster A provides data in units U1 (e.g. basis points, 8-decimal fixed point, wei); cluster B consumes in units U2 (e.g. percentage, 18-decimal fixed point, whole units). Check the provider-interface output shape in cluster A against the consumer math in cluster B.
13. **Cross-cluster pause propagation**: cluster A pauses (local flag) but cluster B's functions that depend on A's state don't check A's pause. When A is paused, B continues operating on stale or partial state.

For each pattern: use the **inventory from Step 2** to identify cross-cluster references quickly. You do NOT need to re-read full cluster source to do the sweep — the inventory has the structural information.

Add cross-cluster findings to the same finding pool with `cross_cluster: true` and the names of both clusters involved.

**Be honest about confidence**: cross-cluster patterns 7 and 8 (economic flows) are pattern-level CANDIDATES for bugs. drozer-lite can flag the class of bug but cannot construct the exploit sequence — the LLM does not do multi-step actor modeling. When flagging, use MEDIUM confidence and note "pattern present, exploit sequence requires manual / `/droz3r` verification".

**Time budget for Step 6**: ~5-10 minutes for a small protocol (≤100KB). Larger protocols may need ~15 minutes.

---

## Step 7 — Emission gates, dedup, aggregate, output

Before dedup, every candidate finding in your working set MUST pass the pre-emission worksheet and three gates (A, C, B). Findings that fail are dropped — **but the drop MUST be recorded in `warnings[]`** so the audit log shows what was filtered and why. Silent drops are forbidden (v0.5.2).

### Step 7.0 — Pre-emission worksheet (MANDATORY before any gate)

For EVERY candidate finding in the working set, fill this 6-field worksheet internally before applying Gates A / C / B. REQUIRED fields must be code-backed — empty REQUIRED fields mean DROP with a `warnings[]` entry `"dropped: <title> | <field-that-failed>"`. This worksheet is the mechanical enforcement of Step 5 rule 4a, Gate A, and Gate C; the existing gate sections below retain authoritative details but the worksheet is the commitment.

| # | Field | Required? | What to fill |
|---|-------|-----------|--------------|
| 1 | Title | Y | One-line title. |
| 2 | Textbook pattern (Y/N) | Y | Mark Y for canonical well-known patterns — CEI/reentrancy, signature replay, reward-debt / MasterChef accumulator, multisig stale-approval after owner removal, ERC4626 first-depositor inflation, flash-loan oracle manipulation, approve-then-transferFrom race, missing slippage on a swap router, missing event on admin setter, missing nonReentrant on a callback-reachable function, similar known patterns. Otherwise N. |
| 3 | Specific-line break | Y if textbook=Y | `file:line` of the specific code that deviates from the textbook safe version + the one-line diff that would fix it. If textbook=Y and this field is unfillable from the current source, DROP. Enforces Step 5 rule 4a. |
| 4 | Exploit sentence | Y | *"An attacker with [ROLE/PERMISSION] calls [FUNCTION] with [CONCRETE INPUT], and the result is [CONCRETE LOSS/IMPACT]."* All four brackets filled from in-scope code; no hypothetical future state (Step 5 rule 5a), no admin-cooperation hedge (Step 5 rule 5b). If any bracket fails, DROP. Enforces Gate A. |
| 5 | Defender sentence | Y | *"This may be a false positive because [specific code-level reason backed by a visible line: a require, a modifier, a state-update ordering, a documented off-chain constraint]."* Strong defender → downgrade one tier (LOW → drop). Weak defender (intuition-only, "probably safe") → keep at original severity. No defender possible from visible code → keep at original severity. Enforces Gate C. |
| 6 | Severity row | Y | Quote the row from the Severity decision table that justifies the chosen severity. If no row matches, default to LOW per the table's no-row rule and document why no row matched. Severity by feel is forbidden. |

Exceptions that pass the worksheet without a full field 4: (a) cross-cluster economic flow candidates from Step 6 patterns 7-13 (explanation prefixed `"Pattern-level candidate:"`, confidence MEDIUM or LOW); (b) INFO-capped hardening items with a one-line justification for keeping. Both must still fill fields 1, 2, 5, 6.

After every candidate passes the worksheet, apply Gate B (reasoning reconciliation) over the full working set, then dedup/consolidation, then output.

### Gate A — Exploit-Sentence Gate (precision)

For each candidate finding, write out internally the following one-sentence exploit statement:

> *"An attacker with [ROLE/PERMISSION] calls [FUNCTION] with [CONCRETE INPUT], and the result is [CONCRETE LOSS/IMPACT]."*

Every bracket must be filled from THIS codebase's source, not from a hypothetical future state.

- `[ROLE/PERMISSION]` must be one of: `anyone` (permissionless), `any holder of X` (where X is a real role/token in this code), `the admin` (if admin is the attacker), `a contract at address Y` where Y is reachable. NOT "a future ERC777 integration", NOT "if a malicious token is whitelisted".
- `[FUNCTION]` must be a function that exists in scope.
- `[CONCRETE INPUT]` must be a value range that exists in the parameter types AND is not already rejected by a require/assert/modifier in the current code.
- `[CONCRETE LOSS/IMPACT]` must be quantifiable: "X tokens moved to attacker", "pool reserves desynced by Y", "user locked out of withdraw", etc. NOT "could cause issues", NOT "may cause confusion".

If any bracket fails, **DROP the finding**. Do not downgrade it to INFO. Do not hedge it with "theoretical". Drop it.

**Two exceptions** — findings allowed through without a concrete exploit sentence:

1. **Cross-cluster economic flow candidates** (Step 6 patterns 7-13). These are explicitly pattern-level flags that drozer-lite cannot construct exploits for. They pass Gate A with `confidence: "MEDIUM"` or `"LOW"` and the explanation must begin with `"Pattern-level candidate:"`.
2. **Informational hardening items** flagged as `severity: "INFO"` (e.g., missing event emission). These pass Gate A but are capped at INFO and must have a one-line justification for why they were kept.

### Gate C — Disprove-Before-Emit (adversarial precision)

After Gate A but before Gate B, for every candidate finding that survived Gate A, write ONE adversarial sentence in your reasoning:

> *Defender's Argument: "This may be a false positive because [specific code-level reason the exploit fails]."*

The reason must be **backed by visible code** in the current source — not intuition, not "probably safe", not "the author surely thought about it." Things that count as a valid defender:

- A specific require/assert that blocks the attack path
- A specific modifier on another function that prevents the precondition
- A specific state update ordering that neutralizes the described race
- A specific modifier/guard on the external callback that prevents reentry
- A specific off-chain constraint documented in the code (comment / NatSpec) that the contract's author relied on

Then apply this rule:

| Defender sentence quality | Action |
|---|---|
| Strong defender backed by a specific line-level guarantee | **Downgrade one tier**. If original is LOW, drop. |
| Weak defender (hand-waving, "usually", "probably") | Keep at original severity |
| No defender possible — no mitigation visible | Keep at original severity (this is a real finding) |

This gate forces the agent to *argue against itself*. Pattern matching plus concrete trace is not enough — the agent must try to disprove the finding using the code. Real bugs survive because no defender argument holds. Plausible-looking FPs get downgraded or dropped because a line-level mitigation exists.

**Visibility (mandatory, v0.5.2)**: For every Gate C decision — downgrade, drop, OR kept-at-original-severity — emit a `warnings[]` entry of the form `"defender_applied: <title> | <one-sentence defender>"` (or `"defender_none: <title> | no mitigation visible"` when no defender is possible). This makes the gate's reasoning auditable post-hoc; silent gate decisions hide regressions.

**Exception**: CRITICAL findings where the defender is only "the admin would not do that" → do NOT downgrade (admin-trust hedging is banned by Step 5 rule 5 anyway).

### Gate B — Reasoning Reconciliation (recall)

Before emitting, scan your own reasoning trace for any dismissal phrases applied to a candidate finding:
- *"actually not a vuln"*, *"self-griefing"*, *"edge case"*, *"would revert anyway"*, *"dead code"*, *"by design"*, *"admin-only so trusted"*, *"mitigated by admin whitelist"*, *"unreachable in practice"*.

For each dismissal, ask: **is the dismissal backed by a hard constraint visible in the current code (a require, a modifier, an enforced invariant) or is it an intuition about operator behavior?**

- Hard constraint → dismissal is valid → keep dropped.
- Intuition about operators, future state, or "by design" without a code-level lock → **restore the finding** at appropriate severity.

This gate prevents the agent from reasoning itself out of reporting real bugs that the pattern matcher correctly identified.

### Dedup, consolidation, and aggregation

After all three gates (A, B, C):

1. Group surviving findings by `(canonical_vulnerability_type, affected_file, affected_function)`. Two findings with the same triple are duplicates — keep the highest-severity.
1a. **Severity-tier output filter** (new in v0.5.1): by default, the `findings[]` array contains only `CRITICAL`, `HIGH`, and `MEDIUM`. `LOW` and `INFO` findings move to the `warnings[]` array as `"low: <title>"` or `"info: <title>"` strings — preserved in output, out of the main findings list. Rationale: LOW/INFO findings are hardening observations; most scoring rubrics penalize them as false positives relative to the expected bug set. A user who wants them (real-audit context) can invoke with `--include-low` or `--full` and the skill restores them to `findings[]`.

2. **Root-cause consolidation** (new in v0.5.1): after dedup, group by `(canonical_vulnerability_type, affected_file)`. If two or more findings share the same vulnerability_type in the same file but hit different functions, apply the **"could one PR fix all of them?"** test:
   - If a single code change would resolve all of them (e.g., `executeTransfer` and `executeTokenTransfer` both missing a nonce, fixed by adding one shared nonce-check helper) → **consolidate into ONE finding**. Name the primary function in `affected_function` and list siblings in the `explanation` with "(also affects: fnA, fnB)".
   - If the fixes are independent (e.g., reentrancy in `withdrawTo` vs access control missing on `setRate` — different fix patterns) → keep as separate findings.
3. The highest-severity finding wins each consolidated slot.
4. Output a single JSON object matching the schema below. By default, no prose around it, no markdown fences. (If the user explicitly asked for a Markdown report, render the same content as a Markdown report — see the Markdown variant at the bottom.)

```json
{
  "scanner": "drozer-lite",
  "version": "0.4.0",
  "profiles_used": ["universal", "reentrancy", "oracle"],
  "files_analyzed": [
    "Token.sol", "Service.sol", "Accountant.sol",
    "Registry.sol", "PauseRegistry.sol",
    "OracleAggregator.sol", "adapters/Adapter.sol",
    "adapters/SourceImpl.sol", "adapters/IAdapter.sol"
  ],
  "clusters": [
    {"name": "PrimaryCluster", "files": 3, "findings": 6},
    {"name": "ControlCluster", "files": 2, "findings": 2},
    {"name": "OracleCluster", "files": 4, "findings": 3}
  ],
  "findings": [
    {
      "vulnerability_type": "lifecycle_state_residue",
      "affected_function": "confirmAction",
      "affected_file": "Service.sol",
      "severity": "HIGH",
      "explanation": "confirmAction requires `address(this).balance >= amount` but the receive() fallback auto-routes incoming native value into the primary state-mutating flow. Any native value sent to the contract is consumed by the auto-route instead of accumulating in contract balance, so the balance-based invariant is permanently brittle.",
      "line_hint": 305,
      "confidence": "HIGH",
      "source_profile": "universal",
      "cluster": "PrimaryCluster",
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
- `version` is `"0.5.6"`.
- `vulnerability_type` MUST be a snake_case canonical tag from the vocabulary at the bottom of this file. **You MUST pick the closest existing tag**; paraphrasing (e.g. writing `"tx.origin authorization"` when the canonical tag is `tx_origin_auth`) is NOT allowed. The vocabulary aligns with SWC Registry and Code4rena taxonomy — labels like `tx_origin_auth`, `missing_access_control`, `missing_input_validation`, `checks_effects_interactions_violation`, `signature_replay`, `reentrancy`, `oracle_staleness`, `division_by_zero`, `missing_timelock` are industry-standard and should match what external scorers and graders expect. Only if the vocabulary genuinely has no close match may you fall back to a short snake_case description — and that is an extraordinary case that should be flagged with a `warnings` entry.
- `severity` is exactly one of `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`. Uppercase.
- `confidence` is exactly one of `HIGH`, `MEDIUM`, `LOW`. Uppercase.
- `source_profile` MUST be one of the profiles you loaded in Step 3.
- `cluster` MUST be one of the cluster names from Step 4.
- `cross_cluster` is `true` if the finding was discovered in Step 6 (cross-cluster sweep), `false` otherwise.
- `swc_id` / `cwe_id` are nullable. Set them when the canonical vocabulary entry has them.
- `findings` may be empty.
- `warnings` should hold any size warnings, profile-load issues, or skipped clusters.

---

## Step 7.5 — Write the report to disk

After producing the findings JSON, write TWO files to the **project root** (the directory the user pointed you at):

1. **`drozer-lite-findings.json`** — the canonical JSON output from Step 7. Machine-readable, schema-compliant.
2. **`DROZER_LITE_REPORT.md`** — the Markdown variant (see Markdown format at the bottom of this skill). Human-readable, severity-grouped, with summary table, per-finding sections, and the honest framing disclaimer.

Use the Write tool. Overwrite if either file already exists (re-runs should produce fresh output).

After writing, tell the user:
```
Wrote:
  drozer-lite-findings.json  (canonical JSON, {N} findings)
  DROZER_LITE_REPORT.md      (Markdown report)
```

If the user specified `--output <path>`, write to that path instead of the project root.

**Do NOT skip this step.** Findings that only exist in conversation context are lost when the session ends. The disk files are the deliverable.

---

## Step 8 — Honest framing

ALWAYS end your response (after the JSON or Markdown report) with this disclaimer, verbatim. Do not soften it. Do not skip it.

> drozer-lite is a pattern-level scanner with cross-file awareness. It catches bugs from a curated checklist of 205 patterns across 14 protocol-type profiles, all derived from real audit findings. It does NOT do multi-step actor reasoning, chain-composition analysis, or formal verification. A clean drozer-lite run is NOT a clean audit. For high-value contracts, use `/droz3r` (the full drozer pipeline) or a human auditor on top of this.

Then add a one-line time disclosure:

> Total wall-clock time: ~XX min. {N} clusters analyzed across {M} files. {K} profiles loaded.

---

## Canonical vulnerability vocabulary (use these as `vulnerability_type`)

These are the snake_case tags. Each tag has a fixed meaning and an optional SWC/CWE cross-reference. If a finding genuinely matches none, use a short snake_case fallback and accept it will not be canonicalized.

**Vocabulary discipline (v0.5.2)**: Where multiple naming forms exist for the same concept (full vs abbreviated, alternate framings), the canonical tag chosen here matches the **unabbreviated industry-standard form** used by SWC Registry / Code4rena / Sherlock. Aliases are listed for cross-reference but MUST NOT be emitted in `vulnerability_type` — emit the canonical only. External scoring rubrics match strings literally; abbreviations lose points to no benefit.

**Tag selection between near-synonyms (v0.5.2)**: Where two canonical tags describe overlapping patterns (e.g. `reentrancy` vs `checks_effects_interactions_violation`), each entry includes a discriminator that resolves the choice. When the discriminator does not clearly resolve, prefer the broader/default tag. Do NOT invent new tags to "split the difference."

**Alias canonicalization (v0.5.5)**: Before emitting `vulnerability_type`, rewrite aliases to canonicals using the table below. This is a **mechanical lookup, not a reasoning step** — if your chosen tag appears in the left column, emit the right column verbatim. External scoring rubrics, finding-dedup tools, and SWC/Solodit cross-referencing pipelines match strings literally; paraphrases cost points against every consumer of the output. The alias list here records paraphrases that real LLM invocations have produced for the same underlying bug — add to this table when a new paraphrase is observed, do not add benchmark-specific mappings.

| Alias (do NOT emit) | Canonical (emit this) | Reason |
|---|---|---|
| `tx_origin_auth` | `tx_origin_authentication` | SWC-115 / Code4rena / Sherlock use the unabbreviated form |
| `reentrancy` (when only CEI ordering is wrong; no proven re-entrant callback needed for the exploit) | `checks_effects_interactions_violation` | Default tag per discriminator in Reentrancy section below |
| `cei_violation` | `checks_effects_interactions_violation` | Abbreviation; same underlying canonical |
| `no_access_control` | `missing_access_control` | SWC-105 unabbreviated |
| `no_input_validation` / `input_validation_missing` | `missing_input_validation` | SWC-123 unabbreviated, consistent with other `missing_*` tags |
| `sig_replay` / `signature_replayable` | `signature_replay` | SWC-121 unabbreviated |
| `div_by_zero` / `divide_by_zero` | `division_by_zero` | Unabbreviated noun form |
| `reward_debt_stale_on_balance_change` / `reward_accounting_bug` | `lifecycle_state_residue` | Reward-debt-on-balance-change is an instance of lifecycle state residue; use the canonical unless a more specific tag applies |
| `no_slippage_check` / `slippage_missing` | `missing_slippage_protection` | Consistent with `missing_*` family |
| `no_event_emitted` / `missing_event` | `missing_event_emission` | Full noun form |

If your chosen tag is NOT in the left column and ALSO not in the canonical list further below, write a short snake_case fallback AND add a `warnings[]` entry `"novel_vulnerability_type: <tag> | <one-line reason no canonical fits>"` so the gap is visible for future vocabulary updates.

### Reentrancy / external call ordering
- `checks_effects_interactions_violation` — External call (or token transfer) executes BEFORE the function updates the state the call's safety depends on. This is the underlying anti-pattern that enables reentrancy and similar timing exploits. **Default tag for any CEI-ordering bug** — pick this unless the proven exploit path specifically requires a re-entrant callback to drain. (SWC-107)
- `reentrancy` — External call passes execution to an attacker-controlled callback that re-enters the same contract (or a related contract sharing state) and exploits mid-execution state. Use ONLY when the proven exploit requires the re-entrant callback path, not just CEI ordering being wrong. (SWC-107, CWE-841)
- `cross_function_reentrancy` — State changed in one function is read inconsistently in another via callback. (SWC-107)
- `callback_hook_reentrancy` — ERC777/721/1155 receiver hook reenters before state finalization. (SWC-107)

### Access control
- `missing_access_control` — State-changing function lacks an authorization check. (SWC-105, CWE-284)
- `tx_origin_authentication` — Authorization decision uses tx.origin instead of msg.sender. (SWC-115) **Canonical tag is the unabbreviated form** to match SWC/Code4rena/Sherlock rubric naming. *Alias (do not emit): `tx_origin_auth`.*
- `privilege_retention_after_transfer` — Deployer or prior owner retains non-owner roles after ownership transfer.
- `rate_limit_bypass` — Sibling function or alternative path bypasses an enforced rate limit.

### Input validation
- `missing_input_validation` — User-supplied parameter is not bounded against an invariant (e.g. `discountBps > 10000`, `fee > 100%`, `amount == 0` on a critical path). (SWC-123, CWE-20)
- `missing_condition_check` — Caller preconditions (time window, state flag, counterparty consent) are not enforced, letting the caller act outside the intended state machine. Use this when the omission is a single missing require/assert, not a broader access-control gap.

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

### Storage / proxy (EVM-specific — only fire on Solidity/Vyper targets)
- `uninitialized_proxy` — Logic contract initializer not disabled. (SWC-118) **EVM only.**
- `storage_layout_collision` — Upgradeable contract storage layout changed without preserving slots. (SWC-124) **EVM only.**
- `uninitialized_storage` — Storage variable defaults to zero and an unset state passes guards. (SWC-109) *Language-agnostic variant: uninitialized struct/resource fields in Move/Rust.*

### EVM-specific (only fire on Solidity/Vyper targets)
- `delegatecall_to_untrusted` — delegatecall target is attacker-controllable. (SWC-112) **EVM only.**
- `receive_auto_route_balance_invariant` — receive()/fallback() auto-calls a state-mutating function, breaking any invariant that uses `address(this).balance`. **EVM only.**
- `erc165_incomplete_coverage` — supportsInterface does not report all interfaces the contract actually implements. **EVM only.**
- `precision_loss_decimal_conversion` — Scaling between different decimal bases truncates value without rounding direction disclosure. *Language-agnostic — applies to any fixed-point math.*

### Other (language-agnostic unless noted)
- `timestamp_dependence` — Critical logic depends on block.timestamp in a manipulable way. (SWC-116) *All chains.*
- `missing_event_emission` — State-changing operation does not emit a corresponding event/log. *All languages.*
- `front_running` — Same-block front-running enables ordering-dependent profit. (SWC-114) *All chains.*
- `vrf_callback_gas` — VRF fulfillment callback exceeds the configured gas limit and reverts. *EVM/Solana.*
- `dust_order_dos` — Residual-below-threshold orders block price levels and DoS the book. *All languages.*
- `pause_time_accumulation` — Time-dependent state continues to accumulate while the protocol is paused. *All languages.*
- `unbounded_loop` — Loop over user-pushable collection with no upper bound. *All languages.*
- `irreversible_admin_action` — Admin parameter change with no timelock or two-step apply. *All languages.*
- `missing_signer_check` — Instruction/transaction does not verify the expected signer/authority. *Solana/Move/Cairo specific equivalent of `missing_access_control`.*
- `arbitrary_cpi` — Cross-program invocation target is attacker-controllable. *Solana equivalent of `delegatecall_to_untrusted`.*
- `missing_account_validation` — Account constraints (owner, discriminator, seeds) not verified. *Solana/Anchor specific.*

---

## Markdown variant (only if the user asks)

Format: Header (profiles, files, clusters) → Summary table → Per-finding sections (vulnerability_type, severity, function, file, cluster, confidence, explanation) → Disclaimer.

---

## Hard rules

1. **Do not** read checklists for profiles you did not load in Step 3.
2. **Do not** invent vulnerability types absent from the canonical vocabulary unless nothing fits.
3. **Do not** report findings without a specific function and file location.
4. **Do not** skip the honest framing disclaimer.
5. **Do not** soften severity ratings to be polite. Use the matrix.
6. **Do not** call any tool other than Read / Glob to gather source. There is no LLM API key in this skill — you ARE the LLM.
7. **Do not** load `icp` or `solana` profiles for Solidity code. They auto-load ONLY when Rust is the detected language and the appropriate framework keywords are present.
8. **Do not** exceed the 1MB total source budget. Refuse politely and recommend `/droz3r`.
9. **Do not** skip Step 6 (cross-cluster sweep) — it is the difference between v0.3.0 and v0.2.x.
10. **Do not** load a profile checklist for every cluster — load each profile checklist ONCE at the start of analysis and reuse it across clusters.
11. **Do not** reveal the inventory map or the cluster plan unless the user asks. They are working artifacts, not output.

---

## Check Authorship Rules

When adding checks to `checklists/*.md`: never use benchmark-specific names (contract names, function names, token tickers). Use generic class-of-bug descriptions only. Provenance lines are the one exception. See `CONTRIBUTING.md` for full rules.
