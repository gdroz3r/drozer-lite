# Solana / Anchor Checklist

> Profile: solana
> Checks: 12
> Source: ported from Drozer-v2 anchor-invariants.md (provenance cited per check)

## Methodology

Solana programs fail in ways Ethereum auditors do not always anticipate: account substitution (type cosplay), missing signer checks, PDA seed collisions, arbitrary CPI, and account-close-then-revive attacks. Apply adversarial thinking at the instruction level: for every `#[derive(Accounts)]` struct, ask what an attacker can substitute, what the Anchor constraints actually enforce, and what assumptions the handler makes that are not verified by those constraints. Prefer `Account<'info, T>` over `AccountInfo` / `UncheckedAccount`. Every `invoke`/`invoke_signed` is a trust boundary: verify the target program, the seeds, and the post-CPI state.

## Checks

### SOL-1: Account Ownership Integrity
**Provenance**: anchor-invariants.md SA1
**Pattern**: An `AccountInfo` or `UncheckedAccount` parameter has no explicit owner check; an attacker substitutes a fake account owned by a malicious program with identical byte layout.
**Methodology**: For every raw `AccountInfo` / `UncheckedAccount`, verify an explicit `account.owner == expected_program_id` check. Prefer typed `Account<'info, T>`. Verify every `/// CHECK:` is documented with the manual validation performed.
**Red flags**:
- `UncheckedAccount<'info>` with no owner check in the handler
- Type-cosplay: same layout, different semantics

### SOL-2: Signer Authorization
**Provenance**: anchor-invariants.md SA2
**Pattern**: Authority/admin accounts are not declared as `Signer<'info>` and the handler does not check `is_signer`, allowing unauthorized callers to invoke privileged operations.
**Methodology**: For every privileged parameter, verify it is `Signer<'info>` OR `#[account(signer)]` OR the handler checks `is_signer`. For PDA-signed CPIs, verify seeds are complete and correct. Verify no instruction can modify authority fields without the current authority signing.

### SOL-3: PDA Derivation Correctness (Canonical Bump & Seed Prefix)
**Provenance**: anchor-invariants.md SA3
**Pattern**: PDA seeds are not length-prefixed and collide (`["ab","c"] == ["a","bc"]`), or a non-canonical bump is accepted, or seeds lack user-specific data allowing cross-user PDA access.
**Methodology**: Verify `find_program_address` is used for canonical bumps. Verify stored bumps match canonical bumps. Verify seeds include user pubkey where user-specific. Verify variable-length seeds are separated.

### SOL-4: CPI Safety
**Provenance**: anchor-invariants.md SA4
**Pattern**: A cross-program invocation targets a program ID that is attacker-controlled, or `invoke_signed` seeds are manipulable, or CPI return values are ignored.
**Methodology**: Verify CPI targets are hardcoded or verified against constants. Verify signer seeds cannot be crafted to sign for unintended PDAs. Verify CPI results are unwrapped. Verify post-CPI state (token balances, account data) is checked.
**Red flags**:
- `invoke(target, ...)` where `target` is from instruction data
- CPI return value discarded

### SOL-5: Token Account Integrity
**Provenance**: anchor-invariants.md SA5
**Pattern**: An SPL token account has no mint/owner/program verification; an attacker passes a worthless token account and receives valuable tokens.
**Methodology**: For every TokenAccount, verify mint matches expected mint, owner matches expected owner, and the program ID is the SPL Token program. For ATAs, verify derivation.
**Red flags**:
- `TokenAccount<'info>` with no constraint on mint or owner
- Generic `AccountInfo` used as a token account with no checks

### SOL-6: Account Closure Safety
**Provenance**: anchor-invariants.md SA6
**Pattern**: An account is closed (lamports drained) but data is not zeroed; attackers revive and re-read stale data, or re-init with attacker authority.
**Methodology**: Verify account data is zeroed before lamports are moved. Verify the discriminator is cleared. Verify same-transaction revival is impossible. Prefer Anchor's `close = ...` to manual drains.

### SOL-7: Initialization Idempotency
**Provenance**: anchor-invariants.md SA7
**Pattern**: A program's `initialize` can be called multiple times or races with the legitimate initialization, re-setting authority to the attacker.
**Methodology**: Prefer Anchor `init` constraint over `init_if_needed`. For manual init, verify an `is_initialized` flag. Verify init parameters cannot be changed after first init.

### SOL-8: Arithmetic Soundness
**Provenance**: anchor-invariants.md SA8
**Pattern**: Release builds without `overflow-checks` wrap silently; casts like `as u64` truncate high bits; division by zero causes a transaction DoS.
**Methodology**: Verify `overflow-checks = true` in `[profile.release]` OR all arithmetic uses `checked_*`/`saturating_*`. Verify casts are bounds-checked. Verify divisors are non-zero. Verify rounding favors the protocol.

### SOL-9: Duplicate Account Prevention
**Provenance**: anchor-invariants.md SA9
**Pattern**: An instruction takes two mutable accounts of the same type; the attacker passes the same account for both, allowing read-then-double-credit exploits.
**Methodology**: For every instruction with 2+ mutable `Account<>` of the same type, verify `require_keys_neq!` or equivalent constraint. Audit `remaining_accounts` loops for duplicate handling.
**Red flags**:
- `source: Account<Vault>, destination: Account<Vault>` with no distinctness check

### SOL-10: Rent Exemption
**Provenance**: anchor-invariants.md SA10
**Pattern**: An account is created with insufficient lamports for rent exemption and is garbage-collected, losing its data.
**Methodology**: Verify account creation uses `Rent::get()?.minimum_balance(data_len)`. Verify reallocs maintain rent exemption at the new size. Audit any direct lamport manipulation.

### SOL-11: Timestamp / Clock Safety
**Provenance**: anchor-invariants.md SA11
**Pattern**: Tight time-dependent logic is vulnerable to validator timestamp drift; slot-skipping causes unexpected gaps.
**Methodology**: Verify deadlines have tolerance windows. Prefer slot height for deterministic timing. Avoid using `unix_timestamp` for randomness or tight windows.

### SOL-12: Error Handling Completeness
**Provenance**: anchor-invariants.md SA12
**Pattern**: `unwrap()` on user input causes DoS; error paths return `Ok(())` silently after a failed check; CPI errors are caught and ignored.
**Methodology**: Audit every `unwrap()` on fallible operations. Prefer `?`. Verify no `Ok(())` is returned after a failed check. Verify CPI errors are propagated.
**Red flags**:
- `ctx.accounts.mint.decimals.unwrap()` on user input
- `if let Err(_) = cpi_call { } else { ... }` with no error propagation
