# Vault Checklist

> Profile: vault
> Checks: 6
> Source: ported from Drozer-v2 vault-invariants.md (provenance cited per check)

## Methodology

Vaults intermediate a share/asset conversion that an attacker will try to manipulate. For every path that converts between shares and assets, identify (a) what controls the numerator and denominator, (b) whether an attacker can influence either atomically (donation, flash-loan, first-deposit), (c) the rounding direction, and (d) whether `totalAssets()` reflects manipulable external state. Test boundary conditions explicitly: `totalSupply == 0`, single wei deposits, full redemption leaving dust, last-strategy removal, and paused external integrations.

## Checks

### VAULT-1: First-Depositor Share Inflation
**Provenance**: vault-invariants.md V3 + V12
**Pattern**: The first depositor mints 1 wei of shares, donates a large amount of the underlying asset, and subsequent depositors round to zero shares; the first depositor then withdraws everything.
**Methodology**: For any share-issuance contract, check whether `_convertToShares` uses virtual offsets (OZ ERC4626 pattern), a minimum initial deposit, or mints dead shares on first deposit. Test the `totalSupply == 0` branch explicitly. Verify whether direct token transfers to the vault affect `totalAssets()`.
**Red flags**:
- `shares = assets * totalSupply / totalAssets` with no virtual offset
- `totalAssets()` returns `token.balanceOf(this)` (donation-manipulable)
- No minimum deposit and no dead-share mint on first deposit

### VAULT-2: ERC-4626 Preview / Max Consistency
**Provenance**: vault-invariants.md V13
**Pattern**: `preview*` and `max*` functions return values inconsistent with actual `deposit`/`withdraw` execution (missing fees, missing pause, wrong rounding direction), breaking external integrations.
**Methodology**: For each of `maxDeposit`, `maxMint`, `maxWithdraw`, `maxRedeem`, verify it reflects actual enforced limits (paused state, whitelist, internal caps) — not `type(uint256).max`. For each of `previewDeposit`, `previewMint`, `previewWithdraw`, `previewRedeem`, verify fees are included and rounding matches the spec (`previewMint` rounds UP, `previewWithdraw` rounds UP).
**Red flags**:
- `maxWithdraw` returns balance while paused
- `previewDeposit` ignores entry fee
- Preview rounds different direction than actual execution

### VAULT-3: Pause Completeness
**Provenance**: vault-invariants.md V14
**Pattern**: When paused, user-facing operations are blocked but admin functions (`rebalance`, `harvest`, `compound`, `migrateStrategy`) still move user assets — admin can act while users cannot exit.
**Methodology**: Enumerate every state-changing function. For each, check whether it is gated by `whenNotPaused`. Any asset-moving admin function that is NOT gated is a trap vector.
**Red flags**:
- `rebalance()` callable while `withdraw()` is paused
- Strategy migration runnable during emergency pause

### VAULT-4: Return-Value Semantics on Deploy/Undeploy
**Provenance**: vault-invariants.md V16 + V11
**Pattern**: `deploy()` / `undeploy()` returns the ACTUAL amount (post-slippage, post-fees), but callers use the REQUESTED amount for downstream accounting.
**Methodology**: For each deploy/undeploy call, check whether the return value or the input parameter is used for `_deployedAmount` bookkeeping, for pro-rata allocation, and for return-to-user amounts. Verify `_deployedAmount` is decremented on undeploy.
**Red flags**:
- `strategy.undeploy(amountRequested); _deployedAmount -= amountRequested;` instead of using the return value
- Multi-strategy withdrawal using requested-amount math
- Leverage undeploy returning 90% with 10% silently lost

### VAULT-5: Strategy Migration & Constructor Validation
**Provenance**: vault-invariants.md V7 + V17
**Pattern**: Strategies are added without validating the underlying protocol's expected asset, and migration does not fully unwind the old strategy before activating the new one.
**Methodology**: For each strategy constructor, verify it checks that the configured asset matches the underlying protocol's expected token. Verify `addStrategy` rejects duplicates and grants the token approval. Verify `removeStrategy` revokes the approval. Verify `migrateStrategy` fully unwinds before activating the replacement and has a timelock / user exit window.
**Red flags**:
- No `require(market.loanToken() == asset)` in constructor
- Migration path that leaves old strategy still approved
- Removed strategy retains unlimited allowance

### VAULT-6: Access Control Principal (Receiver vs Caller)
**Provenance**: vault-invariants.md V18
**Pattern**: `deposit(assets, receiver)` checks `msg.sender` against a whitelist instead of checking `receiver`, allowing a whitelisted user to deposit on behalf of any non-whitelisted address.
**Methodology**: For every function accepting `receiver`/`owner`/`beneficiary`, check which principal is validated against whitelists/limits. `maxDeposit(address)` must accept `receiver` as the limit target.
**Red flags**:
- `require(isWhitelisted[msg.sender])` on a function that credits shares to `receiver`
- `maxDeposit` read against `msg.sender` when `deposit` credits to `receiver`
