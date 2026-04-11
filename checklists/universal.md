# Universal checklist

Always loaded regardless of detected profile. Covers generic Solidity vulnerability patterns that apply to any contract type.

> **Status:** Build Phase 1 placeholder. Full checklist content lands in Build Phase 2 by porting the relevant subset from `/Users/gulhameed/Desktop/Drozer-v2/profiles/` and `/Users/gulhameed/Desktop/Drozer-v2/skills/droz3r/pattern-analysis.md`.

The final universal checklist will cover approximately 40 checks drawn from gap analysis across Virtuals, Morph L2, Oku, Superfluid, Perennial V2, Reserve, AXION, Cork, Blackhole, SecondSwap, Lambo.win, and other benchmark audits.

Categories (to be expanded in Build Phase 2):

- Access control gaps (missing modifiers, tx.origin, unprotected initializers)
- Reentrancy (CEI violations, ERC-777 hooks, callback reentrancy)
- Unchecked external calls (low-level call return ignored, token transfer return ignored)
- Integer safety (division by zero, cast truncation)
- Input validation (zero-address, zero-amount, unbounded loops, array length mismatch)
- State invariants (missing state updates in asymmetric branches, conditional writes)
- Signature basics (missing nonce, missing deadline, ecrecover without validation)
- Event emission gaps (critical state changes without events)
