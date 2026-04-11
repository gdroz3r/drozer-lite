# Governance Checklist

> Profile: governance
> Checks: 6
> Source: ported from Drozer-v2 governance-invariants.md + staking-invariants.md (provenance cited per check)

## Methodology

Governance systems convert economic stake (ve-locks, delegated tokens, NFT membership) into voting power that authorizes fund movement. Attackers try to (a) acquire voting power cheaply (flash loans, bribes, delegation chains), (b) bypass lifecycle constraints (execute before voting ends, cancel legitimate proposals, replay executions), or (c) corrupt aggregate state (slope/bias/totalWeight) via addition without mirroring on removal. For each lifecycle entity (proposal, vote, lock), verify every function checks the entity's state, cannot be called on executed or expired entities, and updates ALL aggregate variables on removal. Build a role-capability matrix: who can propose, vote, queue, execute, cancel, and pause.

## Checks

### GOV-1: Voting Power Integrity (Snapshot vs Live)
**Provenance**: governance-invariants.md G1 + staking-invariants.md S11 (maps to STAKE-11)
**Pattern**: Voting power is read from live balances (flash-loanable) instead of a snapshot taken at proposal creation, or the checkpoint system lets a user double-vote by transferring tokens between addresses.
**Methodology**: For each vote path, verify `getPastVotes(address, snapshotBlock)` is used, not `getVotes(address)`. Verify checkpoints are written atomically on transfer and delegation. Verify no path lets a user vote with the same underlying tokens twice. Verify flash-loaned tokens cannot reach the snapshot block.
**Red flags**:
- `castVote` reads `balanceOf(user)` at current block
- Checkpoint not written in `_beforeTokenTransfer`
- Delegation chain allows circular or multi-hop amplification

### GOV-2: Proposal Lifecycle & Execution Guard
**Provenance**: governance-invariants.md G2 + G13 (maps to STAKE-12 lifecycle state completeness)
**Pattern**: Functions operating on proposals do not check `state(id)`, allowing votes after queuing, fund deposits on executed proposals, or re-execution of executed proposals.
**Methodology**: For every function that accepts a proposal ID, verify it reads `state(id)` or equivalent. Verify `fund()`, `deposit()`, `vote()` cannot be called after queue/execute. Verify `state()` snapshots at transitions rather than re-evaluating live tallies.
**Red flags**:
- `fund(proposalId)` with no state check
- Vote accepted during queued/executed state
- `state()` re-derives from mutable tallies post-queue

### GOV-3: Timelock Security
**Provenance**: governance-invariants.md G4 + G6
**Pattern**: Timelock can be bypassed, its delay can be set to zero, its admin is an EOA, or direct admin calls skip the timelock entirely.
**Methodology**: Verify timelock admin is the governor contract, not an EOA. Verify `setDelay()` itself goes through the timelock. Verify the minimum delay cannot be zero. Verify executed payload hashes match queued payload hashes exactly (no substitution).
**Red flags**:
- `timelock.admin == msg.sender (EOA)`
- `setDelay(0)` allowed
- Executor accepts mismatched targets/values/calldatas from queue

### GOV-4: Aggregate State Consistency on Removal
**Provenance**: governance-invariants.md G11 + staking-invariants.md U27 (maps to STAKE-13 aggregate removal)
**Pattern**: When a nominee/voter/delegate/lock is removed, some aggregates are updated (bias, totalWeight) but not others (slope, changesSum), so future time-weighted extrapolation returns corrupted values.
**Methodology**: For each add/remove function, enumerate every aggregate variable. Verify every aggregate is decremented on removal. For time-weighted aggregates (bias -= slope * time), verify the slope is also corrected. For two-step removal flows (admin + user cleanup), verify the aggregate updates in at least one step, ideally the admin step. Test the zero-aggregate edge case.
**Red flags**:
- `remove()` updates `totalBias` but not `totalSlope`
- Two-step removal where users never complete step 2, leaving inflated aggregate
- Division by zero when all participants removed

### GOV-5: Checkpoint MAX_WEEKS / Loop Coverage
**Provenance**: governance-invariants.md G12 (maps to STAKE-16 MAX_WEEKS coverage)
**Pattern**: A checkpoint loop bounded by `MAX_NUM_WEEKS` is smaller than the maximum lock period divided by `WEEK`, so inactive nominees beyond the window return zero weight (loss of voting power) or the loop exits early with stale state.
**Methodology**: Verify `MAX_NUM_WEEKS >= maxLockPeriod / WEEK` (e.g., 4-year lock needs >= 209 weeks). Verify nominees inactive for > `MAX_NUM_WEEKS` still return correct weight or explicitly return zero with a migration path. Verify permissionless nominee creation cannot spam entries that become stale and waste gas.
**Red flags**:
- `uint256 public constant MAX_NUM_WEEKS = 52;` with 4-year lock support
- `if (weeksPassed > MAX_NUM_WEEKS) return 0` in critical weight calculation

### GOV-6: Exit-Function Balance Manipulation (AC-12 / AC-13)
**Provenance**: governance-invariants.md G14 (maps to AC-12 exit guard + AC-13 balance source)
**Pattern**: `ragequit`/`withdraw` reads `balanceOf(treasury)` as the payout source; MEV searchers sandwich the exit with treasury-draining proposals. Also covers access-control gaps on exit: anyone can trigger another member's exit, or exit is callable outside the member's expected lifecycle window.
**Methodology**: Verify exits use internal accounting, not `balanceOf` live reads. Verify exit-access control restricts callers to the owning member (or an approved delegate). Check whether proposals spending treasury can be timed against exit windows.
**Red flags**:
- `payout = treasury.balanceOf() * shares / totalShares`
- `ragequit(address member)` permissionless and caller unrelated to member
- Time delay between exit request and execution creates a sandwich window
