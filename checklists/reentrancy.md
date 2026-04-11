# Reentrancy Checklist

> Profile: reentrancy
> Checks: 5
> Source: ported from Drozer-v2 invariant-templates.md RE1-4 + universal-invariants.md U4 + amm-invariants.md A6 (provenance cited per check)

## Methodology

Reentrancy is the oldest class of smart-contract exploit and remains a top cause of fund loss. The core question is: during any external call, can control return to the contract (or a cousin contract sharing state) before the current function's state updates are complete? Apply CEI as a checklist, but do not trust it as a guarantee — read-only reentrancy and cross-contract reentrancy can bypass a correct CEI function. For every `call`, `send`, `transfer`, token operation, ERC777/ERC721 callback, flash-loan callback, and external interface call, ask who can gain execution control and what state they can observe or modify.

## Checks

### RE-1: CEI Pattern Violation (Classic Reentrancy)
**Provenance**: invariant-templates.md RE-1 + universal-invariants.md U4
**Pattern**: External call occurs before state updates; an attacker re-enters during the call and observes stale state that permits double-spend or double-withdraw.
**Methodology**: For every function that makes an external call, enumerate state reads and writes. Confirm all writes affecting subsequent guards occur BEFORE the external call.
**Red flags**:
- `token.transfer(to, amount); balances[msg.sender] -= amount;`
- Withdraw path updating balance after `.call` succeeds
- Token minting before external callback

### RE-2: Guard Coverage Gap (Missing nonReentrant)
**Provenance**: invariant-templates.md RE-2
**Pattern**: A function that both modifies state and makes external calls lacks a reentrancy guard, either because the author believed CEI was enough or forgot the modifier.
**Methodology**: For every external-facing state-modifying function that makes external calls, require either `nonReentrant` or structural CEI proof. Prefer belt-and-suspenders (both) on any value-moving path.
**Red flags**:
- `function deposit() external payable { ... }` with no `nonReentrant` but calls a user-supplied hook
- Payable receive function with state writes

### RE-3: Cross-Function Reentrancy
**Provenance**: invariant-templates.md RE-3
**Pattern**: Function A has `nonReentrant`; function B (shares state) does not, so reentering via B during A's external call bypasses the guard.
**Methodology**: Group functions by shared state. Verify every function in a group has reentrancy protection, or structurally cannot observe mid-A state. Watch for view functions used in other contracts' logic (read-only reentrancy).
**Red flags**:
- `deposit` is `nonReentrant`, `balanceOf` is not, another contract calls `balanceOf` during `deposit`'s callback
- Vault share accounting function not guarded while `withdraw` is

### RE-4: Read-After-Call for Security Decisions
**Provenance**: invariant-templates.md RE-4
**Pattern**: A variable read after an external call is used for access control, balance checking, or amount calculation. The callee can manipulate that state during the call.
**Methodology**: For every external call, audit what is read after. Any security-critical read after an external call must either be re-validated or moved before the call.
**Red flags**:
- `balance = balanceOf(user); target.call(...); if (balance > X) { ... }` (but balance was captured before call) — worse: re-read after call
- `require(owner == msg.sender)` read after an untrusted call

### RE-5: Flash Loan / Flash Swap Callback Reentrancy
**Provenance**: amm-invariants.md A6 + perp-invariants.md P4
**Pattern**: Flash-loan callback re-enters the flash-loan contract, the pool, or a downstream protocol to exploit an intermediate state. Also covers liquidation callbacks that allow the liquidated user to re-enter.
**Methodology**: For every flash-loan, flash-swap, or liquidation with a user-controlled callback, verify the invariant (k, repayment, collateral ratio) is checked AFTER the callback and that the callback cannot call back into the flash function or related state-modifying functions.
**Red flags**:
- `flash` entry function not `nonReentrant`
- Callback runs before the pre-callback balance check is cached
- Liquidation bonus paid before the debt repayment is finalized
