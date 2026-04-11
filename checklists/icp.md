# ICP Canister Checklist

> Profile: icp
> Checks: 16
> Source: ported from Drozer-v2 icp-canister-invariants.md (provenance cited per check)

## Methodology

Internet Computer canisters run under a split-message execution model: every `await` is a commit point. Any state change before an await persists even if the callback traps. Apply adversarial thinking to every `#[update]` method: who can call it (authenticated? anonymous?), what state it commits pre-await, what happens if the callback panics, whether state remains consistent under interleaved concurrent calls, and whether the method is idempotent if retried. Check caller authentication explicitly — Anchor's `Signer<'info>` equivalent on IC is `authenticated_caller()` helpers that reject `Principal::anonymous()`. Also verify canister upgrade resilience: pre_upgrade must not trap, timers must be re-registered in post_upgrade, and stable memory must use MemoryManager isolation.

## Checks

### ICP-1: Caller Principal Validation
**Provenance**: icp-canister-invariants.md IC1
**Pattern**: A `#[update]` method does not verify the caller or accepts `Principal::anonymous()`, allowing unauthenticated state mutation.
**Methodology**: For every `#[update]`, verify it calls a centralized `authenticated_caller()` helper that rejects anonymous. Verify controller-only operations use `is_controller()`. Guard functions cannot access method arguments — argument-dependent auth must be in the method body.
**Red flags**:
- `#[update] fn transfer(to, amount)` with no `caller()` check
- Anonymous principal not rejected explicitly

### ICP-2: Inter-Canister Call Atomicity
**Provenance**: icp-canister-invariants.md IC2
**Pattern**: State is modified before an `await`; the callback traps; the pre-await state persists, creating an orphaned debit or stale lock.
**Methodology**: For every async method, identify pre-await state writes. Verify either they are safe to keep on callback failure OR a compensation handler reverses them. Verify no `unwrap()`/`expect()` after any await (a panic becomes a trap that rolls back only the callback). Use `CallerGuard` with Drop cleanup for value-moving methods.
**Red flags**:
- `balance -= amount; ic_cdk::call(...).await.unwrap();`
- Lock acquired pre-await without Drop-based cleanup
- Pre-await writes with no reverse on Err

### ICP-3: Canister Upgrade Resilience
**Provenance**: icp-canister-invariants.md IC3
**Pattern**: `#[pre_upgrade]` traps on large state, heap state is not persisted, or timers are lost after upgrade.
**Methodology**: Verify `pre_upgrade` either does not exist or cannot trap under any input (bounded serialization, no unwrap). Verify persistent data uses stable memory, not heap. Verify version bytes enable schema migration. Verify `post_upgrade` re-registers all timers and handles schema migration. Test with production-scale data.
**Red flags**:
- `pre_upgrade` that calls `unwrap()` on serialization
- Heap `HashMap` used for persistent balances
- `set_timer_interval` not re-registered in `post_upgrade`

### ICP-4: Stable Memory Isolation
**Provenance**: icp-canister-invariants.md IC4
**Pattern**: Two `StableBTreeMap` / `StableCell` structures share the same `MemoryId`, silently overwriting each other's data; or `static mut` introduces non-exclusive mutable references.
**Methodology**: Verify `MemoryManager` is used and every `StableBTreeMap`/`StableCell`/`StableVec` has a unique `MemoryId`. Verify no raw `stable_read`/`stable_write` overlaps managed regions. Verify no `static mut` global state — use `thread_local!` with `Cell`/`RefCell`.
**Red flags**:
- Two maps initialized with the same `MemoryId`
- `static mut GLOBAL: ...`

### ICP-5: Query Response Authenticity (Certified Data)
**Provenance**: icp-canister-invariants.md IC5
**Pattern**: Financial data (balances, prices, ownership) is returned via a `#[query]` without certification, allowing a single malicious replica to forge the response.
**Methodology**: For every query returning security-critical data, verify certified variables are used. Verify `set_certified_data()` is called in the producing update. Verify frontend consumers check the IC certificate, timestamp (<5 min), and witness. Verify assets are served via the canister's certified endpoint, not `raw.icp0.io`.
**Red flags**:
- `#[query] fn get_balance(user) -> Nat` with no certified data
- Asset canister serving via `raw.icp0.io`

### ICP-6: Cycles Drain Resistance
**Provenance**: icp-canister-invariants.md IC6
**Pattern**: Public endpoints can be spammed to drain cycles — either by Candid space/cycle bombs, unbounded inputs, or expensive HTTPS outcalls.
**Methodology**: Verify `inspect_message` rejects unauthenticated ingress where possible. Verify authentication runs before Candid decoding. Verify variable-size inputs (`Vec`, `String`, `Nat`) have size caps. Verify per-caller rate limiting on expensive paths. Verify `freezing_threshold` is set.
**Red flags**:
- `#[update] fn process(data: Vec<u8>)` with no size cap
- HTTPS outcall endpoint with no authentication

### ICP-7: Untrusted Canister Communication
**Provenance**: icp-canister-invariants.md IC7
**Pattern**: Inter-canister calls to untrusted canisters use unbounded-wait semantics, allowing the callee to stall the caller forever, block upgrades, or send a Candid bomb that traps the callback.
**Methodology**: Verify calls to untrusted canisters use `Call::bounded_wait`. Verify response data is validated. Verify `SYS_UNKNOWN` rejection is handled explicitly. Avoid circular call graphs.
**Red flags**:
- `ic_cdk::call(external, ...).await` with no timeout
- Callback that unwraps untrusted Candid without decoding quota

### ICP-8: Controller Security & Decentralization
**Provenance**: icp-canister-invariants.md IC8
**Pattern**: A single controller key can upgrade, stop, or delete a canister holding user funds with no multi-party approval.
**Methodology**: Document controllers and their trust level. Verify high-value canisters have multi-party controllership or a decentralization path. Verify no single controller can unilaterally alter code.

### ICP-9: Timer & Heartbeat Reliability
**Provenance**: icp-canister-invariants.md IC9
**Pattern**: Timer-based security (oracle updates, expiry checks) is lost on upgrade because timers are not re-registered, or heartbeat cost is unbounded and drains cycles.
**Methodology**: Verify all timers are re-registered in `post_upgrade`. Verify heartbeat per-invocation cost is bounded. Verify callbacks do not hold locks across async boundaries.

### ICP-10: Arithmetic & Precision Safety
**Provenance**: icp-canister-invariants.md IC10
**Pattern**: Release builds with `overflow-checks = false` silently wrap on overflow; financial code uses `f32`/`f64`; division-by-zero traps mid-callback.
**Methodology**: Verify `overflow-checks = true` in `[profile.release]` OR all arithmetic uses `checked_*`/`saturating_*`. Verify no floats in financial calculations — use `rust_decimal` or `num_rational::Ratio`. Verify type casts (`as u64`) are bounds-checked. Verify divisors are checked before division.
**Red flags**:
- `balance += amount` without `checked_add`
- `f64` used for token amounts
- `total / stakers.len() as u64` with no zero check

### ICP-11: HTTPS Outcall Safety
**Provenance**: icp-canister-invariants.md IC11
**Pattern**: POST requests to external APIs are sent by every subnet node (N copies), response headers are non-deterministic causing consensus failure, or API credentials leak to node operators.
**Methodology**: Verify POST/PUT uses idempotency keys. Verify a `transform` function normalizes response headers. Verify API credentials are not embedded in request bodies/headers. Verify HTTPS outcall endpoints are authenticated.

### ICP-12: Candid Type Safety
**Provenance**: icp-canister-invariants.md IC12
**Pattern**: A Candid type like `Vec<Null>` encodes to a tiny payload but decodes to a massive in-memory allocation, spiking cycle usage; or a crafted payload exploits CVE-2023-6245.
**Methodology**: Verify `Vec<T>` / `String` / `Nat` parameters have length or magnitude caps. Verify `candid >= 0.9.10`, `ic-cdk >= 0.16.0`, `ic-stable-structures >= 0.6.4`.

### ICP-13: State Consistency Under Interleaving
**Provenance**: icp-canister-invariants.md IC13
**Pattern**: Two concurrent methods pass the same eligibility check pre-await and both proceed, causing double-spend because neither sees the other's commit.
**Methodology**: For every async method with shared state, verify invariants hold under all message interleavings. Use optimistic update + compensation for pre-await writes. Re-read captured variables after await.

### ICP-14: Idempotency & Deduplication on Retry
**Provenance**: icp-canister-invariants.md IC14
**Pattern**: A bounded-wait call returns `SYS_UNKNOWN`; the caller retries; the callee has already processed the first call, resulting in double execution.
**Methodology**: Verify financial operations use dedup IDs (sequence numbers, memo, nonce). Verify the callee rejects duplicate IDs within a window. Verify retry logic never blindly retries non-idempotent operations.

### ICP-15: Principal-Anchored Resource Accounting
**Provenance**: icp-canister-invariants.md IC1 + IC6 (Rule 12 applied to IC)
**Pattern**: Resource accounting (balances, quotas) is keyed by a user-supplied principal rather than the caller, allowing one user to burn another user's quota by invoking a method on their behalf.
**Methodology**: For every method that reads/writes per-principal state, verify the key is `caller()` or explicitly validated to match. No method should accept a principal parameter unless the caller is authorized to act for that principal.
**Red flags**:
- `#[update] fn claim(principal: Principal)` with no caller-to-principal check
- Quota enforcement keyed by `args.user` rather than `caller()`

### ICP-16: Lock & Guard Drop Correctness
**Provenance**: icp-canister-invariants.md IC2 + IC9
**Pattern**: A lock or guard is acquired before an await; the callback traps; the lock is never released because Drop does not run on trap (only on Err).
**Methodology**: Verify all pre-await locks are inside a `CallerGuard` with `call_on_cleanup` (CDK 0.5.1+), not a plain RAII guard. Verify the cleanup is installed before the await. Audit lock-holding timers.
**Red flags**:
- `let _guard = LOCK.lock();` followed by `.await`
- Lock released in an Err branch only
