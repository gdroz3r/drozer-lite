# Universal Checklist

> Profile: universal
> Checks: 110
> Source: ported from Drozer-v2 analyses (provenance cited per check). UNI-96..98 added in v0.3.1 as gap fixes after real-protocol validation. UNI-99..106 added in v0.4.1 as gap fixes after CosmWasm rental-protocol benchmark validation. UNI-107..110 added in v0.4.2 as gap fixes after CosmWasm DEX benchmark validation. All checks describe generic class-of-bug patterns — never benchmark-specific names.

## Methodology

Apply adversarially. For every storage variable, every external-facing function, and every privileged action, ask: who can call it, what state it reads, what state it writes, and what assumptions the surrounding code makes about that state. Trace actual execution paths rather than documented intent. When an invariant is stated in docs, attempt to construct a sequence of calls that breaks it. Prefer evidence from code traces (E3) over pattern matches (E2). Treat every `unchecked`, every external call, every admin setter, and every boundary value (0, 1, type(X).max, array.length == 0/1) as a suspect until proven safe.

## Checks

### UNI-1: Missing / Incorrect Access Control
**Provenance**: universal-invariants.md U1 + invariant-templates.md AC-1
**Pattern**: State-changing functions lack modifiers, use the wrong modifier, or rely on a single role that can be self-granted or front-run during initialization.
**Methodology**: Enumerate every `external`/`public` non-view function. For each, record the authorization path (modifier, inline `require`, or none). Cross-check that admin/owner setters are reachable only by the intended role. Look for `initialize()` without `initializer` guard, role granters that let a role add itself, and emergency functions with weaker protection than the normal path.
**Red flags**:
- Missing `onlyOwner`/`onlyRole(...)`/`onlyGovernor` on state-changing function
- `initialize()` callable multiple times or front-runnable
- Role-admin == role-holder allowing self-grant
- `_setupRole` after deployment without access check

### UNI-2: State Machine / Lifecycle Bypass
**Provenance**: universal-invariants.md U2 + U15 + U16
**Pattern**: Functions operating on lifecycle entities (proposal, position, order) do not check the entity's current state, allowing operations on executed, cancelled, expired, or uninitialized entities.
**Methodology**: For each entity with a lifecycle (created→populated→finalized→consumed), map every function that accepts its ID. Verify each call site either reads a `status` field or asserts preconditions. Flag any function that mutates state without validating the lifecycle position. Check zero/default values do not satisfy "initialized" guards.
**Red flags**:
- `fund()`/`deposit()`/`transfer()` callable on executed proposals
- No `require(state == Active)` on lifecycle-sensitive functions
- Sentinel field defaults (`timestamp == 0`) satisfying `block.timestamp - stored > PERIOD`
- Re-initialization overwriting finalized data
- Temporal guard allows editing AFTER a period expires but BEFORE all settlements from that period are finalized — parameter changes (denomination, rate, price) corrupt pending settlements
- Edit guard checks `expiry < current_time` but not `all_settlements_complete` — the entity appears editable because the period ended, but unsettled obligations still reference the old parameters

### UNI-3: Classic Reentrancy
**Provenance**: universal-invariants.md U4 + invariant-templates.md RE-1
**Pattern**: External call occurs before critical state updates (violates Checks-Effects-Interactions).
**Methodology**: Search for every external call (`.call`, `.transfer`, token transfer, user-supplied target). For each, check what state is read before and written after. If any write that affects subsequent checks happens after the call, the function is re-entrancy unsafe.
**Red flags**:
- Balance/ownership update AFTER `.call` or token transfer
- Absence of `nonReentrant` on payable or token-moving function
- ERC777/ERC721 `onReceived` callbacks on an otherwise trusted path

### UNI-4: Cross-Function / Read-Only Reentrancy
**Provenance**: universal-invariants.md U4 + invariant-templates.md RE-3/RE-4
**Pattern**: Reentrancy guard on function A does not protect function B that reads the same state during A's external call, or a view function returns stale state during another function's external call window.
**Methodology**: Group functions that share state. For each group, check whether a single guard protects the entire group or only individual functions. Identify view functions used for pricing/accounting that are callable during another function's mid-execution window.
**Red flags**:
- `nonReentrant` on `deposit()` but not on `getPrice()` reading the same reserves
- Oracle/price view functions not protected by the same guard

### UNI-5: Missing Zero-Address / Zero-Amount Checks
**Provenance**: universal-invariants.md U5 + invariant-templates.md DF-1
**Pattern**: External parameters are not validated; zero addresses burn tokens, zero amounts skip logic, empty arrays cause silent success.
**Methodology**: For every parameter of every external function, determine whether a zero value would produce undesired behaviour. Check token recipients, approval spenders, configuration setters, and array inputs.
**Red flags**:
- `transfer(to, amount)` with no `require(to != address(0))`
- Setter writes `address(0)` causing irrecoverable state
- `amount == 0` paths skipping fee calculation but still emitting success events

### UNI-6: Integer Overflow / Underflow in Unchecked Blocks
**Provenance**: universal-invariants.md U5
**Pattern**: Arithmetic inside `unchecked { ... }` or using low-level operations wraps around on large inputs.
**Methodology**: Grep `unchecked` and `assembly`. For each block, determine the maximum value each operand can reach across all call sites. Confirm the developer's implicit bound holds.
**Red flags**:
- `unchecked { totalSupply += amount }` without cap
- Counter increment that can flip over many transactions
- Cast `uint256 -> uint128` without bounds check

### UNI-7: Unchecked External Call Return Values
**Provenance**: universal-invariants.md U6 + invariant-templates.md DF-4
**Pattern**: Low-level calls, `transfer`, or non-standard ERC20 tokens return failure silently without reverting.
**Methodology**: For each external call, verify the return value is checked or `SafeERC20` wrappers are used. Treat non-reverting failures as fund-loss bugs.
**Red flags**:
- `token.transfer(...)` without `require` or SafeERC20
- `(bool success, ) = target.call(...)` with unused `success`
- `onERC721Received` never validated on safeTransfer paths

### UNI-8: Controlled Delegatecall
**Provenance**: universal-invariants.md U6 + U8
**Pattern**: `delegatecall` to a user-influenced or loosely-validated target gives an attacker full control of the calling contract's storage.
**Methodology**: Enumerate every `delegatecall`. Trace the target address parameter back to its source. If it can be user-influenced (even indirectly through a config setter) flag immediately.
**Red flags**:
- `delegatecall(msg.data, target)` where target is a setter-modifiable address
- Proxy implementation slot writable by a non-timelocked admin

### UNI-9: Upgrade / Initialization Safety
**Provenance**: universal-invariants.md U8 + invariant-templates.md ST-4
**Pattern**: Upgradeable contracts can be re-initialized, have storage collisions, or allow upgrades without timelock.
**Methodology**: Check for `initializer` modifier, `_disableInitializers()` in constructors, `__gap` storage reserves, and storage-layout compatibility between versions. Verify `upgradeTo` is behind access control AND timelock.
**Red flags**:
- Implementation constructor missing `_disableInitializers`
- `initialize()` without `initializer` modifier
- `__gap` shrunk between versions
- Upgrader is an EOA

### UNI-10: Timestamp Dependence for Security Decisions
**Provenance**: universal-invariants.md U7
**Pattern**: `block.timestamp` used as randomness seed or for tight windows that can be manipulated by validators.
**Methodology**: Grep `block.timestamp` and `now`. For each usage, determine the tolerance to a ~15-second shift. Randomness derived from timestamps is always broken.
**Red flags**:
- `uint256 seed = block.timestamp`
- Deadlines with <1-minute precision enforced for value transfers

### UNI-11: Missing Event Emission on State Changes
**Provenance**: universal-invariants.md U9
**Pattern**: Admin setters, role changes, or critical state transitions do not emit events, preventing off-chain monitoring.
**Methodology**: Build a setter list. For each setter, verify an event is emitted with old and new values. Missing events on role grants, fee changes, or asset onboarding are systemic findings.
**Red flags**:
- `setFee(newFee)` without `FeeUpdated(oldFee, newFee)` event
- Role grant without corresponding event
- Pause/unpause silent

### UNI-12: Unbounded Loops
**Provenance**: universal-invariants.md U10 + invariant-templates.md GR-1
**Pattern**: Loops over arrays that grow with user actions can be gas-bombed to block a function or the entire protocol.
**Methodology**: Identify every loop. For each, determine whether its upper bound is hardcoded, capped, or unbounded. Unbounded loops over user-addable entries are DoS vectors.
**Red flags**:
- `for (uint i; i < users.length; i++)` with permissionless `users.push`
- External calls inside loops without try-catch

### UNI-13: Unvalidated `from` in `transferFrom` (Approval Drain)
**Provenance**: universal-invariants.md U11
**Pattern**: Permissionless function calls `token.transferFrom(from, to, amount)` where `from` is attacker-supplied, draining any user who approved the contract.
**Methodology**: For every `transferFrom` / `safeTransferFrom`, trace who sets `from`. If it comes from calldata and the caller is not validated as `from` or an approved spender, flag as HIGH.
**Red flags**:
- Permissionless external function with `transferFrom(userAddr, ...)` using user's existing allowance
- Permit flows where the permit signer != the operation beneficiary

### UNI-14: Loop External-Call Fragility
**Provenance**: universal-invariants.md U12
**Pattern**: A loop that makes external calls reverts entirely if one iteration fails, blocking all subsequent operations.
**Methodology**: For every loop with external calls, look for try-catch, skip-and-continue, or partial execution patterns. A single paused dependency must not block all withdrawals.
**Red flags**:
- No `try { ... } catch` around strategy/pool external calls in loops
- Attacker-deployable contract that always reverts on transfer can block batch processing

### UNI-15: Weird-Token Incompatibility
**Provenance**: universal-invariants.md U13
**Pattern**: Contract assumes standard ERC20 behavior but supports tokens that charge fees on transfer, rebase, require approve-to-zero, or revert on zero transfer.
**Methodology**: Identify all tokens the contract can interact with (from deployment config, registry, or user-supplied). For each, check fee-on-transfer handling (balance-before/after), USDT approval reset, DAI non-standard permit, decimals assumption, and rebasing impact.
**Red flags**:
- `amount == transferred` assumption after `transferFrom`
- `approve(spender, newAmount)` without zero reset
- Hardcoded 18-decimal math for arbitrary tokens

### UNI-16: Array Boundary Edge Cases
**Provenance**: universal-invariants.md U14
**Pattern**: Swap-and-pop removal, index-based access, or loops fail at `length == 1`, empty arrays, or duplicates.
**Methodology**: For each swap-and-pop, test `last-element removal` explicitly. For each indexed access, verify bounds checks. For each array-modifying function, test empty and single-element cases.
**Red flags**:
- `array[index] = array[array.length - 1]; array.pop()` without zeroing the moved element's companion mapping
- No `index < array.length` check before use

### UNI-17: Post-Commitment State Mutation
**Provenance**: universal-invariants.md U15
**Pattern**: Once state has been finalized, committed, or passed a validation window, it can still be mutated without re-validation.
**Methodology**: For every lifecycle entity, verify each phase is one-way. `initialize` must check for existing state. `consume`/`claim` must re-validate state they read. Mutable fields must not change after proofs are computed.
**Red flags**:
- `initialize()` called twice on same entity overwriting finalized data
- Mutable `partOffset` updated after merkle root computed
- Re-initialization corrupting shared state (registries, oracles)

### UNI-18: Uninitialized-State Guard Bypass
**Provenance**: universal-invariants.md U16
**Pattern**: Zero/default values satisfy guards that assume initialized state (e.g., `block.timestamp - 0 > PERIOD` is always true).
**Methodology**: For every timestamp/existence comparison, ask what happens when the stored field is zero. For every multi-step init, ensure finalize validates ALL intermediate steps completed.
**Red flags**:
- `if (lastClaim != 0)` used to guard distribution but another path skips setting it
- Boolean defaulting to `false` where `false` means both "unvalidated" and "failed"
- Storage map/mapping read for a non-existent key returns zero/default, and the zero value is used downstream without an existence check — e.g., `map.read(user_supplied_key)` returns 0 for an unregistered key, the code hashes 0 with other data, and the hash is used for signature verification. The attacker signs over the zero value to bypass authorization for unregistered keys.
- A registry lookup (oracle registry, whitelist, role mapping) returns a default value for non-members, but the calling code does not assert the returned value is non-zero/non-default before proceeding. The non-member passes the check by operating on the default value.
- `let data = storage_map.entry(key).read(); /* data is 0 for missing key */ validate_signature(data, sig);` — the signature is valid over 0, which is a predictable constant, so any key pair can produce a valid signature

### UNI-19: Temporal Constraint Incompatibility
**Provenance**: universal-invariants.md U17
**Pattern**: A time-bounded operation's guaranteed window is insufficient for the worst-case execution of all required sub-operations.
**Methodology**: For each deadline mechanism, list all operations that must complete within the window. Sum minimum times (including challenge periods). Verify total fits.
**Red flags**:
- 3-hour extension granted but inner operation needs 1-day challenge period
- Nested timers where outer < inner + overhead

### UNI-20: Cross-Environment Resource Parity
**Provenance**: universal-invariants.md U18
**Pattern**: Operation executed in environment A must be reproducible in environment B but B has tighter resource limits (gas, calldata, memory).
**Methodology**: For every cross-environment proof/verification, compare the execution cost in each environment. Account for EIP-150 63/64 forwarding and verifier overhead.
**Red flags**:
- L2 operation that must be re-executed on L1 without gas budget analysis
- Dynamic-cost precompiles unchecked against target env block limit

### UNI-21: Derived-Value Domain Bounds
**Provenance**: universal-invariants.md U19
**Pattern**: Computed values are not capped at their logical maximum before being passed to consuming systems.
**Methodology**: For each derivation (index, position, hash), check the output range matches the consumer's valid input range.
**Red flags**:
- `computedBlock = start + traceIndex + 1` uncapped at `claimedBlock`
- Mapping from large index space to smaller domain without range enforcement

### UNI-22: Work-Reward Decoupling
**Provenance**: universal-invariants.md U20
**Pattern**: Permissionless reward-distribution attributes the reward to `msg.sender` instead of the worker, allowing front-runners to steal.
**Methodology**: For every permissionless claim/distribute, trace who pays cost (gas, bond) vs who receives reward. Mismatch = bug.
**Red flags**:
- `step()` function pays bond to `msg.sender` while evidence was provided by a different party
- Two-step reward where step 2 is permissionless and front-runnable

### UNI-23: Identifier Namespace Collisions
**Provenance**: universal-invariants.md U21
**Pattern**: Unique identifiers can be consumed prematurely, pre-populated for non-existent entities, or become invalid after reordering.
**Methodology**: For each unique ID scheme (nonce, hash, UUID), check whether the ID can be blocked, pre-populated, or invalidated by state changes. Prefer `create2`/salted over nonce-derived for cross-tx safety.
**Red flags**:
- Permissionless data population keyed by future entity address
- Index-based reference breaking after swap-and-pop

### UNI-24: Spec Exhaustive Compliance
**Provenance**: universal-invariants.md U22
**Pattern**: Code implementing a formal spec (instruction set, standard, formula) only handles common cases; edge cases (shift masking, overflow traps, alignment) diverge from the spec.
**Methodology**: For each opcode/rule/formula, compare on-chain implementation against the reference, line by line. Check input masking, overflow behaviour, and undefined-behaviour handling.
**Red flags**:
- Shift amount not masked to 5/6 bits per spec
- Silent wrap where spec requires trap
- Type width mismatch losing high bits

### UNI-25: Error-State Asymmetry in Adversarial Protocols
**Provenance**: universal-invariants.md U23
**Pattern**: In dispute/challenge systems, an error state benefits one party over the other.
**Methodology**: Enumerate every error/revert in a dispute flow. Ask which party benefits. If a panic makes claims unchallengeable, the panic-trigger wins.
**Red flags**:
- `require` in challenge path that only the challenger can hit
- Status value that is simultaneously unattackable and undefendable

### UNI-26: Multi-Step Normalization Ordering
**Provenance**: universal-invariants.md U24
**Pattern**: Non-commutative adjustments (normalize, halve, round) are applied in different orders across branches.
**Methodology**: For each multi-step adjustment, list the steps in order. For each adjacent pair, ask whether swapping changes the result. Verify all branches use the same order.
**Red flags**:
- Branch A: halve-then-adjust; Branch B: adjust-then-halve
- Rounding before scaling losing precision

### UNI-27: Format/Precision Selection Consistency
**Provenance**: universal-invariants.md U25
**Pattern**: Systems with multiple formats (small/large, low/high precision) apply different selection rules across paths.
**Methodology**: Build a format selection table for each path (encode, arithmetic output, decode, conversion). Compare rule sets. Construct boundary values that expose the asymmetry.
**Red flags**:
- Encoding uses more rules than arithmetic output
- `encode(decode(encode(x))) != encode(x)` at boundary

### UNI-28: Representation Gap Integrity
**Provenance**: universal-invariants.md U26
**Pattern**: Values "in the gap" (too precise for small format, not qualifying for large) are silently truncated.
**Methodology**: Identify the gap range using the format selector. Check whether precision loss in the gap stays within stated tolerance and whether it compounds through subsequent calculations.
**Red flags**:
- Format selector uses exponent-only when precision depends on digit count
- Gap value multiplied by gap value

### UNI-29: Aggregate State Removal Consistency
**Provenance**: universal-invariants.md U27
**Pattern**: When an element is removed from a set with aggregate/summary variables, some aggregates are updated and others are not.
**Methodology**: For every aggregate (totalSupply, totalWeight, totalBias, changesSum), verify it is decremented on removal. For time-weighted aggregates, verify the slope is corrected too.
**Red flags**:
- Removal updates `bias` but not `slope`
- Two-step removal where users never complete step 2
- Zero-aggregate edge case causing division by zero

### UNI-30: Stale-Snapshot After Collection Mutation
**Provenance**: universal-invariants.md U28
**Pattern**: A function copies a storage array to memory, mutates the storage array (eviction, swap-pop), then continues using stale memory indices.
**Methodology**: Grep functions that copy storage arrays to memory then call a mutating function. Verify subsequent code re-reads from storage.
**Red flags**:
- `Foo[] memory cache = storageArray; evict(); cache[i]` (stale)
- Swap-and-pop indices reused after reorder

### UNI-31: Prerequisite Update Before Participant Change
**Provenance**: universal-invariants.md U29
**Pattern**: Adding/removing a participant (staker, voter, LP) without first checkpointing accumulated state dilutes existing participants.
**Methodology**: For each `join`/`leave`/`add`/`remove`, verify the checkpoint/accrue function is called first. Verify the accrual is enforced internally, not by external caller convention.
**Red flags**:
- `stake()` pushes to participants array without calling `updateReward()` first
- `retain()` reads weights without calling checkpoint

### UNI-32: Last-Element Array+Mapping Removal
**Provenance**: universal-invariants.md U30
**Pattern**: Swap-and-pop with companion mapping leaves stale mapping entries when removing the last element (self-swap re-assigns it).
**Methodology**: Trace every swap-and-pop that has a companion `mapIds` or index mapping. Test the case where removed index equals the last index.
**Red flags**:
- Map zeroed AFTER swap (self-swap overwrites with stale)
- Existence check `mapIds[h] != 0` returning true for removed elements

### UNI-33: Permissionless Function Privilege Boundary
**Provenance**: universal-invariants.md U31
**Pattern**: A permissionless function accepts a `target` parameter that can be a privileged address with special semantics in another function, bypassing intended behavior.
**Methodology**: Enumerate privileged addresses (retainer, treasury, fee collector). For each permissionless claim/distribute with a `target`, verify it rejects privileged targets.
**Red flags**:
- `distribute(to)` that can be called with `to = treasury` bypassing `retain()` semantics

### UNI-34: Declared Token Compatibility vs. Code
**Provenance**: universal-invariants.md U32
**Pattern**: README/spec declares support for fee-on-transfer, rebasing, blocklist, or upgradeable tokens but code does not actually handle them.
**Methodology**: Read docs for declared compatibility. Compare against code handling of balance-before/after patterns, blocklist reverts on reward paths, and ERC721 safeTransfer on contracts without `onERC721Received`.
**Red flags**:
- Docs say "supports USDT" but code assumes `amount == received`
- Blocklisted fee collector bricks all unstakes

### UNI-35: Role Separation & No Self-Grant
**Provenance**: invariant-templates.md AC-1, AC-2
**Pattern**: A role can grant itself higher privileges, or a single role gates multiple unrelated powers.
**Methodology**: Build a role-capability matrix. Verify every role granter is strictly higher-privilege than the grantee. Check that emergency roles cannot unilaterally elevate.
**Red flags**:
- `RoleA.admin == RoleA`
- Single `onlyOwner` gating both parameter setting and fund movement

### UNI-36: Cross-Contract Access Control Consistency
**Provenance**: invariant-templates.md AC-3 + governance-centralization.md §2
**Pattern**: Contract A restricts function F behind role R, but contract B (caller) has no such restriction, creating a permissionless back-door.
**Methodology**: For every cross-contract call, verify the caller enforces the same or stronger restriction as the target. Flag permissionless wrappers around permissioned functions.
**Red flags**:
- `adapter.split()` public while `core.split()` requires SPLIT_ROLE

### UNI-37: Timelock Scope for Parameter Changes
**Provenance**: invariant-templates.md AC-4 + governance-centralization.md §6
**Pattern**: Parameter changes that affect accounting or user funds can be applied instantly by an EOA admin.
**Methodology**: For every parameter setter that feeds into accounting, verify it is behind a timelock. Setters protected only by `onlyOwner` are instant-rug vectors.
**Red flags**:
- `setFee`, `setRate`, `setOracle` instant with no delay
- Owner is an EOA with no multisig requirement

### UNI-38: Emergency Exit Guarantees
**Provenance**: invariant-templates.md AC-5
**Pattern**: When paused/frozen, users cannot withdraw their own funds.
**Methodology**: Check pause mechanics. Confirm at least one exit path remains available (possibly with penalty) in every paused state.
**Red flags**:
- `whenNotPaused` on `withdraw()` with no alternative
- Liquidation/forced-close functions gated by pause — when the protocol is paused, insolvent positions cannot be liquidated, allowing bad debt to accumulate. Risk management functions (liquidation, deleverage) should remain operational during pause
- Deposit cancellation gated by pause — users who deposited before the pause cannot recover their funds

### UNI-39: Monotonic State Progression
**Provenance**: invariant-templates.md TL-1
**Pattern**: Phased state (epochs, rounds) regresses to a previous phase under some path.
**Methodology**: For each phase counter, identify every write. Confirm writes are monotonic increments.
**Red flags**:
- `currentEpoch` writable to arbitrary value
- Timestamp-based epoch boundary that resets on pause/unpause

### UNI-40: Past-Epoch Immutability
**Provenance**: invariant-templates.md TL-2
**Pattern**: Data from a completed epoch can still be modified after the next epoch starts.
**Methodology**: For each epoch-keyed mapping, identify setters. Verify they revert once the epoch is past.
**Red flags**:
- `setEpochReward(epochId, amount)` with no completion check

### UNI-41: Cooldown Bypass
**Provenance**: invariant-templates.md TL-3
**Pattern**: Multiple code paths, transferring staked tokens, or restaking can reset or skip a cooldown.
**Methodology**: For each cooldown, enumerate all paths that read it. Check whether any bypass exists (token transfer, partial restake, emergency withdraw).
**Red flags**:
- `transferFrom` of staked token shifts cooldown to attacker
- Emergency withdraw without equivalent cooldown

### UNI-42: Deadline Validity
**Provenance**: invariant-templates.md TL-4
**Pattern**: Stale transactions (past deadline) can still execute.
**Methodology**: Grep all operations that accept a `deadline`. Verify `require(block.timestamp <= deadline)`.
**Red flags**:
- Deadline parameter accepted but never checked
- Deadline check under a conditional that can be skipped

### UNI-43: Sequence / Step Ordering
**Provenance**: invariant-templates.md TL-5
**Pattern**: A later step in a multi-step operation can execute without the earlier step completing.
**Methodology**: For each multi-step flow, enumerate the required preconditions for each step. Verify each step re-validates its preconditions.
**Red flags**:
- `finalize()` that does not check `populate()` ran
- Step 2 reads storage set by step 1 without verifying step 1's completion

### UNI-44: Bounded Iteration
**Provenance**: invariant-templates.md GR-1
**Pattern**: Loops lack an explicit or implicit cap, enabling gas-bomb DoS.
**Methodology**: For every loop, document the upper bound. If the bound is user-controlled without cap, flag.
**Red flags**:
- `for (; i < userProvided;)` with no limit

### UNI-45: Array Growth Limits
**Provenance**: invariant-templates.md GR-2
**Pattern**: A user-pushable array has no max size, allowing an attacker to fill it and brick iteration.
**Methodology**: For every dynamic array growable by external calls, check for a cap (explicit or economic).
**Red flags**:
- `strategies.push(...)` without `require(strategies.length < MAX)`

### UNI-46: External Calls in Loops
**Provenance**: invariant-templates.md GR-3
**Pattern**: A loop makes an unbounded number of external calls; one failing call reverts the whole batch.
**Methodology**: Cross-reference with UNI-14. Require try-catch or skip-and-continue for each loop external call.
**Red flags**:
- `for (...) target[i].call(...)` without try-catch

### UNI-47: Bounded Cleanup on Delete
**Provenance**: invariant-templates.md GR-4
**Pattern**: Deleting an entity runs unbounded work, DoSing the deletion path itself.
**Methodology**: For each delete path, check it completes in constant or bounded gas.

### UNI-48: Arithmetic Rounding Direction
**Provenance**: invariant-templates.md MF-3
**Pattern**: Rounding direction favors the user instead of the protocol, enabling dust extraction.
**Methodology**: For every `mulDiv` / division in asset/share math, verify the direction: deposits round shares DOWN, withdrawals round assets DOWN.
**Red flags**:
- `shares = amount * totalSupply / totalAssets` rounding up
- Fee calculation rounding toward user

### UNI-49: Donation / Direct Transfer Corruption
**Provenance**: invariant-templates.md MF-6 + vault-invariants V12
**Pattern**: Accounting reads `balanceOf(address(this))` instead of internal state, allowing direct transfers to corrupt accounting.
**Methodology**: For each accounting function, check whether it uses `balanceOf` or internal counters. `balanceOf` is donation-vulnerable.
**Red flags**:
- `totalAssets()` returns `token.balanceOf(this)`
- First depositor calculates shares from `balanceOf`

### UNI-50: First-Depositor Share Inflation
**Provenance**: invariant-templates.md MF-5 + vault-invariants V3
**Pattern**: First depositor mints 1 wei, donates large amount, causing subsequent depositors to round to zero shares.
**Methodology**: For any share-issuance contract, verify virtual shares/assets (OZ pattern), minimum deposit, or dead-shares mint on first deposit.
**Red flags**:
- `shares = assets * totalSupply / totalAssets` with no virtual offset and `totalSupply == 0` edge case

### UNI-51: Atomic Value Transfer
**Provenance**: invariant-templates.md MF-7
**Pattern**: Sender's balance decreases by X but receiver's increases by Y != X (minus fees).
**Methodology**: For each transfer, verify source debit == destination credit + documented fee.

### UNI-52: Solvency Invariant (contractBalance >= sum(userOwed))
**Provenance**: universal-invariants.md U3 + invariant-templates.md MF-1
**Pattern**: Protocol-tracked liabilities exceed actual asset holdings.
**Methodology**: For each token held, trace: (balance on contract) vs (sum of user claims + protocol fees). Verify the invariant holds under every execution path.
**Red flags**:
- Withdrawal path decrements `userShares` but not `totalShares`
- Fee accrual double-counted

### UNI-53: No Free Extraction
**Provenance**: invariant-templates.md MF-2
**Pattern**: A sequence of calls allows withdrawing more value than deposited (net of fees and yield).
**Methodology**: Model the protocol as a closed economy. Attempt to construct a cycle that produces profit without external input.

### UNI-54: Fee Bounds Enforcement
**Provenance**: invariant-templates.md MF-4
**Pattern**: Fee setters allow values exceeding documented maxima.
**Methodology**: For each fee setter, verify `require(fee <= MAX)`. Check cumulative fees across multiple paths.
**Red flags**:
- `setFee(uint256 fee)` with no upper bound

### UNI-55: Storage Slot Uniqueness
**Provenance**: invariant-templates.md ST-1
**Pattern**: Proxy and implementation use conflicting storage layouts, or assembly sstore overwrites another variable.
**Methodology**: For upgradeable contracts, verify storage gap reservation and layout compatibility via tools like `hardhat-upgrades`. For assembly slot access, verify slot calculation.

### UNI-56: Initialization Completeness
**Provenance**: invariant-templates.md ST-2
**Pattern**: Functions read storage variables before they are initialized, getting default zero values.
**Methodology**: For each storage variable, verify at least one write occurs before any read on every reachable path.

### UNI-57: Mapping Key Uniqueness (encodePacked Pitfalls)
**Provenance**: invariant-templates.md ST-3 + DF-3
**Pattern**: `abi.encodePacked` with multiple variable-length types produces colliding keys.
**Methodology**: Grep `abi.encodePacked`. For each, verify no two variable-length types are adjacent. Use `abi.encode` or add length prefixes.
**Red flags**:
- `keccak256(abi.encodePacked(name, symbol))` where both are user-supplied

### UNI-58: Signed Data Completeness
**Provenance**: invariant-templates.md DF-2 + signed-data-completeness §1
**Pattern**: A digest omits fields the function uses for decisions, allowing relayer substitution.
**Methodology**: For each signature verification, build a SIGNED DATA BINDING TABLE: list every field used post-verification. Every used field must be signed.
**Red flags**:
- `deadline` used but not part of signed payload
- `callGasLimit` honored but not signed

### UNI-59: Nonce / Replay Protection
**Provenance**: invariant-templates.md DF-5 + signed-data-completeness §4
**Pattern**: Signatures can be replayed due to missing nonce, non-atomic nonce increment, or nonce omitted from hash.
**Methodology**: Verify nonce is in the signed digest, incremented atomically, and scoped per-signer.

### UNI-60: Taint Boundary at External Returns
**Provenance**: invariant-templates.md DF-4
**Pattern**: Return values from external contracts are consumed without validation.
**Methodology**: For each external call return used in a calculation, verify sanity bounds.

### UNI-61: Oracle Staleness Protection
**Provenance**: invariant-templates.md OR-1
**Pattern**: Oracle price reads omit a staleness check, allowing stale values to drive critical decisions.
**Methodology**: For each oracle read, verify `require(updatedAt >= block.timestamp - heartbeat)` or equivalent. Check that every oracle reader uses the same threshold (see UNI-65).

### UNI-62: Manipulation-Resistant Pricing
**Provenance**: invariant-templates.md OR-2
**Pattern**: A price is derived from spot reserves or `balanceOf`, enabling flash-loan manipulation.
**Methodology**: Every price used for liquidation/borrowing/mint must use TWAP, Chainlink, or time-weighted sources.

### UNI-63: Oracle Graceful Degradation
**Provenance**: invariant-templates.md OR-3
**Pattern**: Oracle failure (revert, stale, zero) bricks the protocol permanently.
**Methodology**: Verify a pause path exists on oracle failure rather than a hard revert.

### UNI-64: Multi-Source Oracle Validation
**Provenance**: invariant-templates.md OR-4
**Pattern**: High-value operations rely on a single price feed with no cross-check.
**Methodology**: For liquidations and large swaps, verify price is cross-checked against a second source or bounded by a circuit breaker.

### UNI-65: Feed Consistency Across Readers
**Provenance**: invariant-templates.md OR-5
**Pattern**: Different functions read the same oracle with different freshness thresholds, producing inconsistent behavior.
**Methodology**: Identify every reader of each oracle feed. Verify all use the same freshness threshold and fallback.

### UNI-66: Parameter Scope Declaration
**Provenance**: parameter-scope-analysis.md §1
**Pattern**: Admin parameters are used by calculation functions with no documentation of whether they apply retroactively or only to future operations.
**Methodology**: Build a PARAMETER SCOPE TABLE for every admin-modifiable storage variable. Row: parameter, setter, reader functions, temporal scope, retroactive. If scope is undocumented AND the parameter is read by historical calculations, flag.

### UNI-67: Retroactive Calculation Prevention
**Provenance**: parameter-scope-analysis.md §2
**Pattern**: An admin parameter change alters results for a PAST period after the period ends but before users claim.
**Methodology**: For each admin-modifiable parameter, ask: "If admin changes it at T, does calling a view function for T-1 return a different result?" If yes, the historical value must be snapshotted.
**Red flags**:
- `getEpochReward(epochId)` reading the live `rewardRate`
- `pendingReward()` using the current rate for past periods

### UNI-68: Locked-Position Integrity
**Provenance**: parameter-scope-analysis.md §3
**Pattern**: A user commits to a locked position under specific terms; admin changes the global terms and the change retroactively applies.
**Methodology**: For each locking/staking/vesting mechanism, check whether terms are stored per-position or read from global state on each access.
**Red flags**:
- `penalty = globalPenaltyRate` read at exit time instead of lock time
- APY read from global state for pre-existing locks

### UNI-69: Timing-Adversary Resistance on Admin Changes
**Provenance**: parameter-scope-analysis.md §4
**Pattern**: Admin parameter updates create a window where attackers front-run or back-run for profit.
**Methodology**: For each admin setter, check timelock protection and whether front-run/back-run is profitable.

### UNI-70: Cross-Function Consistency of Parameter Reads
**Provenance**: parameter-scope-analysis.md §5
**Pattern**: `preview*` and actual operation use different snapshots of the same parameter, producing contradictory results.
**Methodology**: For each parameter read by view and state-changing functions, verify both use the same snapshot semantics.

### UNI-71: Boundary Safety on Parameter Updates
**Provenance**: parameter-scope-analysis.md §6
**Pattern**: Setters accept values that individually seem valid but collectively cause division-by-zero, overflow, or impossible states.
**Methodology**: For each setter, trace arithmetic expressions using the parameter. Check for zero denominator, >100% basis points, `min > max`, and upper-bound overflow.

### UNI-72: Privilege Enumeration / Centralization Surface
**Provenance**: governance-centralization.md §1
**Pattern**: Admin functions are undocumented; maximum damage under malicious admin is unclear.
**Methodology**: Enumerate every `onlyOwner`/`onlyRole` function. For each, document worst-case damage. Rate: can admin mint without backing, drain user funds, block operations, set fees to 100%?

### UNI-73: Operation Blocking Powers
**Provenance**: governance-centralization.md §3
**Pattern**: Admin can pause exits while entries remain open, trapping users.
**Methodology**: Check whether exits can be blocked independently of entries and whether transfers are pausable.

### UNI-74: Irreversible Admin Actions
**Provenance**: governance-centralization.md §5
**Pattern**: Admin actions cannot be undone (set-once mappings, remove-without-claim).
**Methodology**: For each admin action, verify an inverse exists.

### UNI-75: Ownership Transfer Two-Step
**Provenance**: governance-centralization.md §6
**Pattern**: Single-step ownership transfer can send ownership to `address(0)` or wrong address irrecoverably.
**Methodology**: Prefer `Ownable2Step`.

### UNI-76: Router Permissionless Entry Points
**Provenance**: router-multicall-invariants.md R1
**Pattern**: Permissionless `execute`/`multicall` dispatches commands where `from`/`owner` is attacker-supplied, draining anyone who approved the router.
**Methodology**: For every command with a `from`/`owner` parameter, verify `msg.sender == from` or equivalent. For every command with `receiver`, verify the attacker cannot send victim's funds to themselves.

### UNI-77: Approval Persistence on Router
**Provenance**: router-multicall-invariants.md R2
**Pattern**: Users grant approval to a router; any permissionless command can then spend their tokens.
**Methodology**: Build an APPROVAL FLOW TABLE for the router. For each spend path, verify msg.sender is validated as the token owner.

### UNI-78: Permit Frontrunning on Router
**Provenance**: router-multicall-invariants.md R3
**Pattern**: An attacker extracts a permit signature from the mempool and submits it with different downstream commands.
**Methodology**: Verify permit signer matches the operation beneficiary. Check DAI non-standard permit handling.

### UNI-79: Router Identity Confusion
**Provenance**: router-multicall-invariants.md R4
**Pattern**: Vaults/protocols see the router as the depositor; per-address limits apply to the router instead of end users.
**Methodology**: Check whitelist and maxDeposit enforcement site.

### UNI-80: Router Token Residual / Sweep
**Provenance**: router-multicall-invariants.md R6
**Pattern**: Tokens left in the router between commands can be swept by the first caller.
**Methodology**: Verify the router never holds tokens across transactions; if a sweep exists, verify it cannot race a victim's in-flight transaction.

### UNI-81: Compound-Fork Share Rounding Subadditivity
**Provenance**: compound-fork-integration.md §1
**Pattern**: `floor(a) + floor(b) < floor(a+b)` causes single aggregated redemption to require more shares than held.
**Methodology**: Compare sum of individual mints vs single aggregated redeem. Check whether protocol donates shares to absorb rounding.

### UNI-82: Compound Treasury Fee Activation Risk
**Provenance**: compound-fork-integration.md §2
**Pattern**: Governance of an external Compound fork enables a treasury fee; the integrating protocol reverts or silently loses amount.
**Methodology**: Check whether the adapter reads `treasuryPercent` and how it handles non-zero results.

### UNI-83: Supply-Cap / Borrow-Cap DoS
**Provenance**: compound-fork-integration.md §3
**Pattern**: External supply cap filled by a whale blocks all subsequent deposits.
**Methodology**: Check whether deposits handle cap reversion and whether an alternative yield source exists.

### UNI-84: High-Utilization Redemption DoS
**Provenance**: compound-fork-integration.md §4
**Pattern**: `redeemUnderlying` reverts when pool cash < requested; protocol has no fallback.
**Methodology**: Verify try-catch and fallback source chains.

### UNI-85: Empty-Market First-Depositor Amplification
**Provenance**: compound-fork-integration.md §6
**Pattern**: Protocol auto-deposits into newly-created markets vulnerable to first-depositor attack.
**Methodology**: Check whether yield sources are validated as established before auto-deposit.

### UNI-86: External Reward Capture from Yield Sources
**Provenance**: compound-fork-integration.md §11 + yield-source-integration.md §7
**Pattern**: Lending pools distribute governance tokens / Merkle rewards to the depositor (the protocol contract); users have no claim path.
**Methodology**: Verify a claim or generic `execute()` function exists and has fair distribution logic.

### UNI-87: Partial vs Full Redemption DoS
**Provenance**: yield-source-integration.md §1
**Pattern**: Protocol forces full balance redemption; if transfers are disabled and liquidity is low, users are permanently locked.
**Methodology**: Verify partial redemption exists or an equivalent escape hatch.

### UNI-88: Bad-Debt Cascade / Idle-Balance Drainage
**Provenance**: yield-source-integration.md §2
**Pattern**: Attacker deposits into an insolvent source (absorbing bad debt) then withdraws from idle balance, draining the protocol.
**Methodology**: Verify deposits check source solvency; verify redemption fallback ordering does not leave stale `depositedAmounts`.

### UNI-89: Skip/Disable Flag Consistency
**Provenance**: yield-source-integration.md §4
**Pattern**: A `skipForWithdrawal` flag is applied inconsistently across functions (correct for withdraw, wrong for deposit).
**Methodology**: Build a function × flag × checked? table.

### UNI-90: FCFS on Insolvency
**Provenance**: yield-source-integration.md §6
**Pattern**: When a yield source goes insolvent, first redeemer takes everything while later redeemers get nothing; no pro-rata loss sharing.
**Methodology**: Verify loss-sharing mechanism or document FCFS behavior as intentional.

### UNI-91: Negative-Yield Accounting
**Provenance**: yield-source-integration.md §5
**Pattern**: `depositedAmounts -= amountRedeemed` underflows when yield source returns less than deposited.
**Methodology**: Verify the accounting handles `amountRedeemed < deposit` gracefully.

### UNI-92: Yield-Leakage via Return-Value Mismatch
**Provenance**: yield-source-integration.md §8 + vault-invariants V16
**Pattern**: Yield source returns more than requested; excess is silently left in the contract or given to wrong recipient.
**Methodology**: Trace every `amountReturned` vs `amountRequested` path. Verify the excess is explicitly routed.

### UNI-93: Emergency Function Input Validation
**Provenance**: yield-source-integration.md §10
**Pattern**: `emergencyWithdrawFromYieldSources(address[])` accepts arbitrary addresses; accounting can be corrupted by a rogue address.
**Methodology**: Verify input validation against registered sources.

### UNI-94: Before/After Balance Pattern Consistency
**Provenance**: yield-source-integration.md §12
**Pattern**: Some paths use `balanceAfter - balanceBefore`, others trust nominal amount; inconsistent handling breaks fee-on-transfer or rebasing tokens.
**Methodology**: Identify every transfer path. Verify consistent before/after or consistent nominal usage across paths.

### UNI-95: Irreversible Yield-Source Configuration
**Provenance**: yield-source-integration.md §9
**Pattern**: `underlyingToVToken[token]` is set once with no unset; a wrong or deprecated mapping is permanent.
**Methodology**: Verify every configuration mapping has both set and unset admin paths.

### UNI-96: ERC-165 Inherited Interface Coverage
**Provenance**: drozer-lite v0.3.1 — class-of-bug: supportsInterface override omits interfaces implemented by ancestor contracts, breaking ERC-165-based integration detection.
**Pattern**: A contract's `supportsInterface(bytes4)` only reports the interface it was explicitly registered for, not every interface its parent contracts implement. Downstream integrators who check `supportsInterface(ParentInterface.selector)` get false and refuse integration.
**Methodology**: For every `supportsInterface` override, enumerate every ancestor contract's interface (including upgradeable/proxy libraries). Verify the override returns true for each. Prefer `return super.supportsInterface(interfaceId) || interfaceId == type(IThis).interfaceId` to the fully-enumerated OR chain to avoid drift on future inheritance changes.
**Red flags**:
- `supportsInterface` returns `interfaceId == type(IThis).interfaceId` only, not OR'd with `super`
- New interface added to the contract but supportsInterface not updated
- AccessControl + Enumerable + custom interface but only one is reported
- Interface-detection-based integration docs (e.g., marketplaces) not tested against actual supportsInterface

### UNI-97: Precision Loss in Decimal Conversion
**Provenance**: drozer-lite v0.3.1 — class-of-bug: silent truncation when scaling values between different decimal bases, rounding direction undocumented and inconsistent with the inverse operation.
**Pattern**: A function converts a value between different decimal bases (e.g. 18→8, 18→6, 8→18) and silently truncates. The rounding direction is not documented, not user-controlled, and not consistent with the inverse operation.
**Methodology**: Grep every `amount * 10**X`, `amount / 10**X`, `_convertToNDecimals`, or explicit `mulDiv`/`div` between two known-different decimal bases. For each, verify:
1. The rounding direction matches the intent (user-owed amounts round UP for the user, fees round UP for the protocol).
2. The inverse conversion is actually inverse — `convertUp(convertDown(x))` should equal `x` only at the base-grid boundary.
3. A round-trip of the same amount through two conversions does not compound loss more than a stated tolerance.
4. Boundary values (0, smallest non-zero, smallest that rounds up) behave correctly.
**Red flags**:
- `truncatedAmount = amount / 1e10;` with no rounding-up branch on the withdrawal path
- Deposit and withdrawal paths use different rounding directions silently
- Loss accumulates per-operation and is not recorded or refunded to the user
- Conversion comment says "truncates" but callers treat the result as exact

### UNI-98: receive()/fallback() Auto-Route Balance Invariant Break
**Provenance**: drozer-lite v0.3.1 — severity calibration fix for a pattern class where the receive()/fallback() path re-enters a state-mutating function and any invariant that reads `address(this).balance` becomes permanently brittle. This check is structurally HIGH, not MEDIUM.
**Pattern**: A contract has a `receive()` or `fallback()` payable function that unconditionally forwards `msg.value` into a state-mutating function in the same contract (deposit, wrap, stake, mint, buy). Another function in the same contract uses `address(this).balance` as part of an invariant check (e.g., `require(address(this).balance >= amount)` before a refund / withdraw / return / claim). Because the auto-route consumes incoming native value before it can accumulate, the balance-based invariant can be permanently unsatisfiable, or at minimum becomes dependent on chain-specific semantics for how native value can enter the contract without invoking `receive()`.
**Methodology**: For every `receive()` and `fallback()` function in the cluster:
1. Check whether it unconditionally forwards `msg.value` into a state-mutating function (one that writes storage, mints tokens, or calls an external contract with value).
2. Grep the entire cluster for any `address(this).balance` read used in a `require`, arithmetic, or branch that affects a user-visible decision (refund, withdraw, claim, redeem, rescue).
3. If both conditions hold, trace whether there is ANY path by which native value can enter the contract WITHOUT invoking `receive()` (e.g., `selfdestruct(to)` from another contract, direct balance credit from a privileged precompile, block reward to COINBASE if the contract is a miner/proposer, chain-specific system transfers). If no such path exists, the invariant is permanently broken. If one exists, the invariant is brittle and subject to operational assumptions outside the source.
**Red flags**:
- `receive() external payable { f(); }` where `f()` is any state-mutating function in the same contract
- `fallback() external payable { ... f(); }` similarly
- Any function with `require(address(this).balance >= amount, ...)` whose sibling contract has an auto-routing `receive()`/`fallback()`
- A "rescued" or "cancelled" accumulator variable whose only payout path depends on contract balance growing via future external transfers
- Comments or docs saying "buffer provides liquidity" or "accumulated value drains to users" but no actual code path produces non-auto-routed inbound value
**Severity rule (HARD)**: When the balance-based invariant is read in a user-facing function (withdraw, refund, claim, redeem, rescue, confirm, settle), this check MUST be rated at least HIGH. Do NOT downgrade to MEDIUM due to uncertainty about chain-specific native-transfer semantics — the correct finding is HIGH with a note that exploitability depends on operational assumptions the auditor should flag and verify with the protocol team. Severity miscalibration on this pattern is itself a finding-quality bug.

### UNI-99: Approval / Permission Persistence After Action Reversal
**Provenance**: drozer-lite v0.4.1 — class-of-bug: an action grants a permission as a side effect, and the reversal of that action does not revoke the permission, leaving the actor with unauthorized access.
**Pattern**: An action (bid, deposit, stake, register, subscribe) grants an approval, role, or allowance as a side effect. The corresponding reversal action (cancel bid, withdraw, unstake, deregister, unsubscribe) removes the primary state entry but does NOT revoke the permission that was granted alongside it. The actor retains the ability to operate on the entity (transfer, spend, execute) despite no longer having a stake or valid reason for access.
**Methodology**: For every function that grants an approval or permission as a side effect of a primary action:
1. Identify the corresponding reversal function (cancel, withdraw, remove, unstake, deregister).
2. Verify the reversal function explicitly removes the same approval/permission.
3. Check both per-token approval lists AND global operator/role mappings.
4. If the grant is conditional (e.g., only when `auto_approve` is true), verify the revocation also fires under the same condition.
**Red flags**:
- `approvals.push(sender)` in a bid/deposit path but the cancel/refund path only removes the bid entry, not the approval
- `grantRole(OPERATOR, sender)` on registration but `revokeRole` absent from deregistration
- `approve(spender, amount)` on stake but no `approve(spender, 0)` on unstake
- Toggle function (call once to create, call again to cancel) where the first call grants approval and the second call removes the primary record but not the approval
- Any path where an actor can: (1) perform action to gain permission, (2) reverse action to recover funds, (3) use retained permission to operate on the asset without cost

### UNI-100: Asymmetric Settlement Across Parallel Transfer Paths
**Provenance**: drozer-lite v0.4.1 — class-of-bug: multiple functions can move the same asset but only one includes payment/settlement logic, allowing the other to bypass payment entirely.
**Pattern**: A system has two or more functions that transfer ownership or move the same asset (e.g., `transfer` vs `send`, `transferFrom` vs `safeTransferFrom`, `withdraw` vs `emergencyWithdraw`, `redeem` vs `rescue`). One path includes settlement logic (payment to seller, fee deduction, accounting update, reward distribution). Another path transfers the asset without performing the same settlement, creating a bypass.
**Methodology**: 
1. Enumerate every function that changes ownership of an asset or moves value out of the contract.
2. Group these functions by the asset class they operate on.
3. For each group, build a comparison table: function name | settlement logic present? | fee deducted? | accounting updated? | events emitted?
4. If ANY function in the group skips settlement that another function performs, flag. Pay special attention to wrapper functions that call a shared internal `_transfer` without the outer settlement layer.
**Red flags**:
- `transfer()` includes payment settlement but `send()` calls `_transfer()` directly without settlement
- `withdraw()` updates accounting but `emergencyWithdraw()` does not
- Public `_transfer_nft()` helper is callable by approved addresses and bypasses the sale/auction settlement in `transfer_nft()`
- A function that takes a `recipient` parameter (allowing caller to send to another address) and a parallel function that forces `msg.sender` as recipient — the first may skip payment checks the second enforces
- Two functions that both call `check_can_send()` but only one settles the associated financial obligation (bid, deposit, escrow)

### UNI-101: Destructive Operation Without Obligation Settlement
**Provenance**: drozer-lite v0.4.1 — class-of-bug: a burn/delete/close function destroys an entity with active obligations (deposits, rentals, locks), erasing records but not settling or refunding, making deposited funds permanently unrecoverable.
**Pattern**: A destructive operation (burn, delete, remove, close, self-destruct, deactivate) destroys an entity that carries active obligations — deposits held against it, active rentals or leases, pending reward claims, locked collateral, open orders, or unresolved escrows. The destruction erases the entity's records from storage, but the funds associated with those obligations remain in the contract with no recovery path. Affected users can no longer call cancel/refund/claim because the entity no longer exists.
**Methodology**: For every destructive function (burn, remove, close, delete, deactivate, self-destruct):
1. Identify what data is erased (the entity's full storage record, including nested structs, vectors, mappings).
2. Check whether any of the erased data includes: deposit amounts, active rental/lease records, pending claims, locked collateral, open bids, escrowed funds.
3. Verify the function checks for zero active obligations BEFORE allowing destruction. Acceptable patterns: `require(obligations.length == 0)`, `require(deposit_amount == 0)`, iterating obligations and refunding each before deletion.
4. If the function only checks ownership/approval but not obligation status, flag.
**Red flags**:
- `burn()` checks `check_can_send()` (ownership) but not whether `rentals.len() > 0` or `bids.len() > 0`
- `closePosition()` deletes the position record without checking `pendingRewards > 0`
- `deleteAccount()` while staking/delegation entries still reference the account
- `remove(tokenId)` erases a token struct that contains a Vec of deposit records
- Any destructive function where the authorization check is ownership/approval only, without an obligation-settlement check

### UNI-102: Heterogeneous Collection Without Type Discrimination
**Provenance**: drozer-lite v0.4.1 — class-of-bug: items of different types with different economic parameters are stored in the same collection, and operations iterate without filtering by type, allowing cross-type exploitation (e.g., paying in denomination A but receiving refund in denomination B).
**Pattern**: A collection (Vec, array, mapping, linked list) stores items of different subtypes, distinguished by a type flag, enum field, or discriminant. Operations that search, iterate, cancel, settle, or finalize items in the collection match by identity fields (address, ID, period) but do NOT filter by the type discriminant. This allows an operation designed for subtype A to match and operate on a subtype B item that has different economic parameters (denomination, rate, fee structure, cancellation policy).
**Methodology**:
1. Identify every collection that stores items with a type discriminant field (e.g., `item_type: bool`, `order_side: enum`, `position_type: u8`, `category: u8`).
2. For every function that searches/iterates the collection, check whether the search predicate includes the type discriminant.
3. If the search matches by (address + period) or (address + id) but ignores (type), verify whether the matched item's economic parameters (denomination, rate, terms) could differ from what the calling function assumes.
4. If a function reads denomination/rate/terms from a TYPE-LEVEL config (e.g., `shortterm_rental.denom`) but the matched item was created under a DIFFERENT type's config (e.g., `longterm_rental.denom`), flag as HIGH — this enables cross-denomination value extraction.
**Red flags**:
- A `rentals` Vec stores both short-term and long-term entries with a `type` flag, but cancel/finalize functions search by `(address, period)` without checking `type`
- An order book stores buy and sell orders in the same array with a `side` field, but settlement iterates without filtering by side
- A positions collection mixes collateralized and uncollateralized positions, but liquidation logic applies uniformly
- A function reads the denomination from a type-level config struct but the matched item in the shared collection was created under a different type's denomination
- Cancel function for type A matches a type B item and refunds using type A's denomination instead of the item's stored denomination

### UNI-103: Payment-Gated Transfer Allows Beneficiary Mismatch
**Provenance**: drozer-lite v0.4.1 — class-of-bug: a transfer function looks up payment amount by recipient address, but the caller can specify any recipient including one with no payment, causing a zero-payment asset transfer.
**Pattern**: A function combines asset transfer with payment settlement. The payment amount is looked up from a mapping or list keyed by the recipient address (e.g., bids, deposits, escrow entries). The caller can freely specify the recipient parameter. If the recipient has no entry in the payment mapping, the amount defaults to zero and the transfer proceeds without payment to the previous owner. Alternatively, the caller specifies a recipient different from themselves to avoid their own payment being consumed, then cancels their payment entry for a full refund.
**Methodology**:
1. For every function that transfers an asset AND looks up a payment amount by a caller-supplied address parameter:
   a. Check whether the function reverts when no payment entry exists for the specified recipient (amount == 0 case).
   b. Check whether the function validates that the payment amount meets the listed/required price.
   c. Check whether the caller is constrained to specify themselves as the recipient, or can specify any address.
2. If the function proceeds with transfer when `amount == 0` (no matching payment), flag as HIGH — the asset is transferred for free.
3. If the function does not validate `amount >= listed_price`, flag as HIGH — the asset can be transferred for less than the listed price.
**Red flags**:
- `amount = bids[recipient].offer` defaults to 0 when no bid exists, and the function has a branch that proceeds with transfer when `amount == 0`
- Transfer function accepts `recipient` as a parameter (not forced to `msg.sender`), allowing the caller to route the transfer to an address with no active bid
- Caller can: (1) place a bid to gain approval, (2) call transfer with a DIFFERENT recipient who has no bid (zero payment), (3) cancel their own bid for full refund
- No `require(amount >= listed_price)` check between the payment lookup and the ownership transfer
- The `amount > 0` branch sends payment to the previous owner, but the `amount == 0` branch still transfers ownership

### UNI-104: Numeric Type Width Insufficient for Token Decimals
**Provenance**: drozer-lite v0.4.1 — class-of-bug: price or amount parameters use a narrower integer type than the token amounts they interact with, making normal-value operations impossible for high-decimal tokens.
**Pattern**: Price, amount, or rate parameters in message/function signatures use a narrower integer type (e.g., `u64`, `uint64`, `uint32`) than the token amount type used in the contract's arithmetic (e.g., `u128`, `Uint128`, `uint256`). For tokens with 18 decimals, `u64` maxes at ~18.4 tokens — any price above ~$18 for a $1-token is unrepresentable. This creates a functional ceiling where normal-value operations silently fail or are impossible to express.
**Methodology**:
1. For every price, amount, or rate parameter in external function signatures and message structs, note the integer type width.
2. For each such parameter, trace how it's used in arithmetic with token amounts. Note the token amount type (typically the widest type in the system).
3. If the parameter type is narrower than the token amount type AND the protocol accepts arbitrary user-specified denominations (tokens with varying decimals), flag.
4. Calculate the practical ceiling: `max_value / 10^decimals` for common decimal counts (6, 8, 18). If the ceiling is below reasonable real-world values for the parameter's purpose (e.g., < $1000 for a rental price), flag.
**Red flags**:
- `price_per_day: u64` but `deposit_amount: Uint128` (u128) in the same system
- `amount: u64` in a withdrawal function but `info.funds[0].amount` is `Uint128`
- `fee: u64` but fee is multiplied with `Uint128` amounts, silently capping the effective fee range
- Any `u64` price/amount field in a protocol that accepts arbitrary token denominations (user-chosen, not hardcoded)
- Withdrawal function requires multiple calls to extract a normal-value deposit because the per-call `amount` parameter is too narrow

### UNI-105: Stored Constraint Not Enforced at Consumption Point
**Provenance**: drozer-lite v0.4.1 — class-of-bug: a configuration function stores a constraint field (availability window, whitelist, maximum, deadline) but the consuming function that should enforce it never reads or checks it, making the constraint decorative.
**Pattern**: A configuration or listing function accepts and stores a constraint parameter (available period, whitelist, max participants, allowed tokens, deadline, minimum amount, geographic restriction). The consuming function that should enforce this constraint (reservation, deposit, bid, claim, register) operates on the same entity but never reads or validates the stored constraint. The constraint exists in storage but has zero enforcement — users can bypass it simply by never encountering a check.
**Methodology**:
1. For every configuration/listing function, enumerate every field it writes to storage.
2. For each stored field, classify it as: (a) data field (description, name, URI — informational), or (b) constraint field (period, whitelist, max, min, deadline, rate — should restrict behavior).
3. For each constraint field, find ALL consuming functions that operate on the same entity. Verify the constraint field is READ and produces a REVERT or behavioral change in each consumer.
4. If a constraint field is stored but never read by any consuming function, flag as MEDIUM — the feature is broken, not just missing.
**Red flags**:
- `available_period` set in listing function but reservation function checks `minimum_stay` only, ignoring `available_period` entirely
- `max_participants` stored on entity creation but join function has no cap check
- `allowed_tokens` whitelist stored but deposit function accepts any denomination
- `deadline` stored but claim function checks `block.timestamp` against a different value
- `auto_approve` flag stored for one rental type but the approval function for that type never reads it
- Any field in a config struct that is written in the setter and read ONLY in query/view functions (never in state-changing functions)

### UNI-106: Listing-Gate Bypass on Unlisted Entities
**Provenance**: drozer-lite v0.4.1 — class-of-bug: a function that should only operate on listed/active entities does not check the listing status flag, allowing operations on unlisted, delisted, or never-listed entities.
**Pattern**: An entity has a listing status field (`is_listed`, `active`, `status`, `enabled`) that is set by a listing function and cleared by an unlisting function. Consumer functions (bid, reserve, purchase, deposit, subscribe) that should only operate on listed entities do not check the listing status. This allows: (1) operations on entities that were never listed, (2) operations on entities that were explicitly delisted, (3) exploitation of stale configuration (e.g., `auto_approve` from a previous listing) on a currently unlisted entity.
**Methodology**:
1. For every entity with a listing/status flag, enumerate: (a) the function that sets it to active/listed, (b) the function that sets it to inactive/unlisted, (c) all consumer functions that operate on the entity.
2. For each consumer function, verify it checks the listing status flag early in execution (before accepting funds, granting approvals, or modifying state).
3. Pay special attention to configuration fields that PERSIST across list/unlist cycles. If `auto_approve`, `price`, `denomination`, or other economic parameters are set during listing and NOT cleared during unlisting, check whether consumers of these fields are guarded by the listing status.
4. If a consumer function accepts funds or grants permissions without checking listing status, flag. Severity depends on whether the stale configuration enables value extraction.
**Red flags**:
- `bid()` function does not check `is_listed == true` before accepting funds and granting approval
- `reserve()` function accepts deposits for unlisted properties/assets
- `purchase()` function operates on delisted items using stale price/denomination from a prior listing
- Unlisting function sets `is_listed = false` but does NOT clear `auto_approve`, `price`, or `denomination` — these persist and are used by consumer functions that skip the listing check
- Any consumer function that reads economic parameters (price, denomination, approval mode) from the entity without first verifying the entity is currently listed

### UNI-107: Nested Loop Depth Exceeds Gas Budget
**Provenance**: drozer-lite v0.4.2 — class-of-bug: nested iteration over user-growable collections produces O(N^k) complexity with k≥2, exceeding the block gas limit and permanently DoSing the function for affected users.
**Pattern**: A function iterates over collection A (size P). For each item, it iterates over collection B (size F). For each pair, it iterates over a range R (size E). The total work is O(P × F × E). Even with individual caps on P, F, and E, the PRODUCT can exceed the block gas limit. This is distinct from UNI-12 (single unbounded loop) — the issue is the nesting depth, not any single loop being unbounded.
**Methodology**:
1. For every function with nested loops (loop inside a loop), compute the worst-case product of all loop bounds.
2. For each bound, determine: is it hardcoded? Is it configurable? Is it user-determined? Can it grow over time (e.g., epochs since first action)?
3. Compute worst-case iterations: multiply all bounds. If the product exceeds ~50,000 (conservative gas budget for CosmWasm/EVM), flag.
4. Check whether the function can be called in batches (e.g., claim per-position, claim per-epoch range). If no batching mechanism exists and the function is mandatory (e.g., claim before close), the DoS is permanent.
**Red flags**:
- `for position in positions { for farm in farms { for epoch in start..=current { ... } } }` — O(P×F×E)
- Reward calculation that iterates over all epochs since a user's first deposit with no epoch-range parameter
- `close_position` requires `claim()` first, and `claim()` has O(N^3) complexity — DoS on claim blocks close
- No "partial claim" or "skip positions" mechanism exists
- Config parameters cap individual collections (e.g., max 100 positions, max 10 farms) but their product (1000+) is not capped

### UNI-108: Temporal Parameter Allows Retroactive / Past Values at Creation
**Provenance**: drozer-lite v0.4.2 — class-of-bug: a creation function accepts a user-supplied temporal parameter (start time, start epoch, activation date) without enforcing it is in the future, allowing retroactive entity creation that breaks reward distribution, billing, or scheduling invariants.
**Pattern**: An entity with a time-based lifecycle (farm, vesting schedule, auction, subscription, rental) accepts a `start_time` or `start_epoch` parameter at creation. The parameter is validated for basic sanity (> 0, < end) but is NOT validated against the current time/epoch. This allows creating entities that "started in the past," retroactively assigning rewards, obligations, or access to historical periods that other participants have already settled.
**Methodology**:
1. For every creation function that accepts a start_time/start_epoch parameter, verify it is enforced as `>= current_time + 1` or `>= current_epoch + 1`.
2. Check the default value when the parameter is omitted — if it defaults to `current + 1`, verify the explicit path has the same constraint.
3. Trace what happens if start is set to a past value: are rewards retroactively assigned? Do billing periods extend into the past? Can the creator claim historical periods?
**Red flags**:
- `start_epoch = params.start_epoch.unwrap_or(current_epoch + 1)` but no `ensure!(start_epoch >= current_epoch + 1)` for the explicit case
- Validation checks `start < end` and `end > current` but not `start > current`
- A farm/schedule created with past start_epoch assigns emissions to epochs where participants already claimed, creating unfair distribution
- Default path is safe (`current + 1`) but explicit path bypasses the constraint

### UNI-109: Self-Call Identity Confusion
**Provenance**: drozer-lite v0.4.2 — class-of-bug: a contract calls itself (via submessage, internal execute, or self-invoke) and the called function uses `info.sender` for authorization, but the sender is now the contract itself instead of the original user, causing authorization checks to fail or be bypassed.
**Pattern**: A function performs a two-step operation by calling itself: step 1 initiates (stores context in a buffer), step 2 is triggered via a self-call (SubMsg or wasm_execute to self). The second step's `info.sender` is the contract's own address, not the original user. If step 2 has an authorization check like `require(sender == receiver)` or `require(sender == user)`, it fails because sender is the contract. Conversely, if step 2 has an authorization check like `require(sender == admin || sender == contract)`, the self-call bypasses user-level restrictions.
**Methodology**:
1. For every SubMsg or wasm_execute that targets the contract's own address (`env.contract.address`), identify the function being called.
2. Check what `info.sender` is used for in the called function. If it's used for authorization, it will be the contract address, not the original caller.
3. Check whether any receiver/beneficiary validation compares against `info.sender` — this will fail for the self-call case.
4. Check whether any privilege check accepts the contract's own address — this could be a bypass vector.
**Red flags**:
- `wasm_execute(env.contract.address, &ExecuteMsg::ProvideLiquidity { receiver: user, ... }, funds)` where `ProvideLiquidity` checks `ensure!(receiver == info.sender)` — fails because info.sender is the contract
- Two-step LP provision: step 1 swaps half, step 2 provides balanced LP. Step 2's sender check rejects the self-call.
- A singleton buffer stores context for the reply handler — if two users trigger step 1 in the same block, the second overwrites the first's buffer
- Any function with `if info.sender == env.contract.address { /* special path */ }` that grants elevated privileges

### UNI-110: Permissionless Entity Creation Bypasses Protocol-Intended Parameters
**Provenance**: drozer-lite v0.4.2 — class-of-bug: a permissionless creation function allows the creator to specify parameters that the protocol intended to control (e.g., fee rates, reward schedules), enabling creators to set these to zero or adversarial values to the protocol's detriment.
**Pattern**: A permissionless function (e.g., create pool, create farm, register market) accepts parameters that affect protocol revenue or user protections. These parameters are stored per-entity and used in subsequent operations. The protocol intended to enforce minimum values (e.g., minimum protocol fee, minimum collateral ratio) but the creation function either has no minimum check or the minimum is 0. Creators can set `protocol_fee = 0`, `collateral_ratio = 0`, or `insurance_fund_share = 0` to attract users while depriving the protocol of revenue or safety margins.
**Methodology**:
1. For every permissionless creation function, enumerate every parameter that is stored per-entity and affects protocol revenue or user protection.
2. For each such parameter, check whether a protocol-level minimum is enforced. If the only validation is `fee.is_valid()` (which may only check `< 100%`), a zero value passes.
3. Check whether the protocol has a global/config-level fee that overrides per-entity fees. If not, the per-entity fee IS the protocol fee.
4. Compare against industry standard: Uniswap charges a protocol fee at the factory level; Curve charges admin fees globally. If this protocol charges fees per-entity with no floor, flag.
**Red flags**:
- `create_pool(pool_fees: PoolFee)` where `pool_fees.protocol_fee` can be set to 0 by the creator
- `is_valid()` only checks `fee < 100%`, not `fee >= MINIMUM_PROTOCOL_FEE`
- No global fee override exists — the per-entity fee is the only fee
- Protocol documentation states "fees are collected on every swap" but code allows zero-fee pools
- Pool/farm/market creator can front-run legitimate creation with a zero-fee version to attract liquidity away from fee-bearing entities
