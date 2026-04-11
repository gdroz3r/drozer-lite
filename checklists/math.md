# Math Checklist

> Profile: math
> Checks: 6
> Source: ported from Drozer-v2 universal-invariants.md U24-U28 + invariant-templates.md MF3 (provenance cited per check)

## Methodology

Numerical code in smart contracts fails in specific, learnable ways: rounding in the wrong direction (dust extraction), division-before-multiplication (precision loss), order-dependent normalization across branches, format-selection asymmetry, and gap-range precision collapse. Attackers look for every place where operations are non-commutative, where formats differ across paths, and where the rounding direction is not documented. When a function implements a mathematical specification, compare the implementation to the reference line-by-line, paying particular attention to shift masking, overflow trapping, and alignment semantics.

## Checks

### MATH-1: Rounding Direction (Protocol-Favorable)
**Provenance**: invariant-templates.md MF-3
**Pattern**: Asset/share math rounds in the user's favor instead of the protocol's, enabling dust extraction via repeated deposit/withdraw cycles.
**Methodology**: For every `mulDiv` and division in asset↔share conversion, verify the rounding direction. Deposits must round shares DOWN (user receives at least this many). Withdrawals must round assets DOWN (user receives at most this many). Fee calculations must round toward the protocol.
**Red flags**:
- `shares = amount * totalSupply / totalAssets` with implicit round-up
- `mulDiv(a, b, c, Math.Rounding.Up)` on a user redemption path
- Symmetric deposit/withdraw rounding (both up or both down)

### MATH-2: Divide-Before-Multiply Precision Loss
**Provenance**: universal-invariants.md U3 (Slither divide-before-multiply)
**Pattern**: `(a / b) * c` loses precision when `a / b` truncates; the correct form is `(a * c) / b`.
**Methodology**: Grep every division followed by multiplication within the same expression tree. Apply Slither's `divide-before-multiply` detector. For each hit, reorder to multiplication-first unless overflow prevents it (use `FullMath.mulDiv`).
**Red flags**:
- `fee = (amount / 10000) * feeRate` where `feeRate < 10000`
- `reward = (balance / periodLength) * duration`

### MATH-3: Multi-Step Normalization Ordering
**Provenance**: universal-invariants.md U24
**Pattern**: Non-commutative adjustments (normalize, halve, round, scale) are applied in different orders across branches of the same function.
**Methodology**: For each multi-step adjustment sequence, list the steps in order for every branch. For each adjacent pair (A, B), ask whether swapping changes the result. If yes, verify the order is consistent across all branches.
**Red flags**:
- Large-value branch: halve-then-adjust; small-value branch: adjust-then-halve
- Pre-halving modification that should have been post-halving

### MATH-4: Format / Precision Selection Consistency
**Provenance**: universal-invariants.md U25 + U26
**Pattern**: A library supports multiple formats (small/large, compressed/full) but the format selector differs across paths — encoding uses more criteria than arithmetic output, for example, so values that qualify for the large format via encoding are downcast by arithmetic.
**Methodology**: Build a FORMAT SELECTION RULE TABLE per path. Verify all rows are identical. Construct boundary values that expose the asymmetry and trace them through each path. Verify `encode(decode(encode(x))) == encode(x)`.
**Red flags**:
- Encoding uses [digit count, exponent]; arithmetic output uses [exponent] only
- Boundary values where decode loses information

### MATH-5: Representation Gap Integrity
**Provenance**: universal-invariants.md U26
**Pattern**: Values "in the gap" between small and large representations are silently truncated beyond stated tolerance; the loss compounds when two gap values are multiplied.
**Methodology**: Identify the gap range from the format selector's criteria. Measure precision loss for values in the gap. Verify it stays within any stated tolerance (e.g., "1 ULP accuracy"). Test that `gap_value * gap_value` does not exceed acceptable error.
**Red flags**:
- Selector checks exponent only, precision depends on digit count
- No explicit tolerance specification in code or spec
- Gap-value multiplication in a hot path

### MATH-6: Aggregate Removal & Stale Snapshot
**Provenance**: universal-invariants.md U27 + U28
**Pattern**: Aggregate state variables (totalWeight, totalSlope, sumBias, totalSupply) are decremented on addition but not on removal, or a function copies a storage array to memory before mutating the storage array and then uses the stale copy for arithmetic.
**Methodology**: For each aggregate variable, verify every removal path decrements it. For time-weighted aggregates, verify slope corrections. For every function that copies storage to memory then mutates storage, verify subsequent reads use the current storage, not the stale copy. Test swap-and-pop cases where the pre-eviction index no longer maps to the same element.
**Red flags**:
- `remove()` updates `bias` but not `slope`
- `uint256[] memory cache = storageArray; evict(); cache[i]` used after eviction
- Swap-and-pop last-element case that leaves a stale companion mapping entry
