# Changelog

## v0.5.4 — Revert v0.5.3; restore worksheet baseline (2026-04-17)

**Headline**: v0.5.3's two-quote / named-reference tightening of worksheet field 3 was a regression in clean-room cross-run validation. Rolled back to the v0.5.2 worksheet contract. SKILL.md content is byte-identical to v0.5.2 except for version strings.

### What v0.5.3 broke

The named-reference safe-form requirement penalized findings whose canonical fix is a one-line check rather than a structural pattern (input validation, missing access control, missing condition checks). Agents marked these as `textbook=Y`, then could not produce a verbatim safe form from a NAMED industry reference (because no such named reference exists for "add the missing require"), so the finding dropped. Net effect in cross-run validation:
- Multiple legitimate findings dropped (regressions on cases where v0.5.2 scored 1.0 or near-perfect).
- One previously-clean case gained a new false positive.
- The intended target (pattern-spam emissions on textbook DEX/share/balance patterns) was only marginally suppressed.

### Root cause of the v0.5.3 design failure

1. **Field 2's textbook list was not exhaustive** ("similar known patterns" / "etc."). Agents extrapolated unpredictably and over-marked findings as textbook=Y, dragging legitimate findings into the new strict field 3.
2. **The named-reference requirement assumed every textbook pattern has a documented safe form in industry sources**. This is true for structural patterns (CEI, ERC4626 first-depositor, Curve invariant) but false for one-line-fix patterns (input validation bounds, missing access guards). Penalizing findings of the latter class for not having a "named reference" is wrong.
3. **The change did not address the actual structural problem**: pattern-matching scanners always emit when patterns are present, and "this contract is intentionally a teaching fixture" is a judgment that pattern-level enforcement cannot make. Worksheet enforcement at the single-agent level cannot fully solve this.

### What is preserved from v0.5.2

All of the v0.5.2 changes that did real work in cross-run validation:
- Step 7.0 worksheet (6-field structured commitment).
- No-silent-drops rule.
- Gate C visibility entries in `warnings[]`.
- Vocabulary discipline rules (unabbreviated canonical, near-synonym discriminator).
- `tx_origin_authentication` and `checks_effects_interactions_violation` as canonical tags.

### What is NOT being attempted in v0.5.4

No replacement for the v0.5.3 textbook-break tightening. The lesson from this iteration is that further single-agent worksheet enforcement is unlikely to break past the v0.5.2 baseline — the residual gap requires either (a) a structurally different validation mechanism (e.g., independent-context second-agent validation of worksheet entries), or (b) acceptance of the v0.5.2 baseline as the current ceiling pending a different evaluation corpus. No new methodology change ships in v0.5.4.

### Anti-bloat audit

| Change | Type | Lines | Files modified |
|---|---|---|---|
| Field 3 cell — restored to v0.5.2 wording | revert | net −2 | 1 |
| Field 3 enforcement rationale paragraph — removed | revert | net −5 | 1 |
| Version bump (v0.5.3 → v0.5.4) | edit | net 0 | 1 |
| **Total** | — | **−7 net** | **1 file (SKILL.md)** |

SKILL.md shrinks from 597 → 595 lines (back to v0.5.2 size).

---

## v0.5.3 — Two-quote textbook break (2026-04-17)

**Headline**: Methodology-only refinement to the v0.5.2 worksheet. Targets the residual failure mode where agents fill worksheet field 3 with vague phrasing ("should add nonReentrant", "needs slippage parameter") that satisfies the structural check but doesn't actually prove a textbook deviation. Addresses pattern-spam emissions on contracts where the patterns are present but the textbook safe form is genuinely matched (or has acceptable alternatives).

### Methodology change

**Worksheet field 3 — two-quote requirement**. When `textbook=Y` (field 2), field 3 now requires:
1. The offending code as it exists in the current source, quoted verbatim with `file:line`.
2. The textbook-safe equivalent quoted verbatim from a NAMED industry reference (OpenZeppelin / Uniswap V2 or V3 / ERC4626 spec / SWC mitigation / Chainlink integration guide / Curve / etc.).
3. A one-sentence statement of the structural gap between (1) and (2).

The finding DROPS if any of:
- Either code quote is missing or paraphrased rather than verbatim.
- No recognized reference applies (in which case field 2 was wrongly marked Y — the finding is not a textbook-class case).
- The structural gap is just a hardening pattern with acceptable alternatives (e.g., dead-share mint on first deposit instead of OZ virtual offsets, balance-after deltas instead of explicit reentrancy guard, post-transfer detection instead of blocklist enforcement).

### Rationale

Pattern presence is the easiest property to over-claim. The v0.5.2 worksheet made Step 5 rule 4a a REQUIRED field, but a REQUIRED field that accepts handwave defeats its own purpose. Forcing two verbatim quotes plus a NAMED reference creates structural pressure: the agent either produces the comparison or admits the textbook-pattern claim was unsupported. The named-reference requirement specifically addresses the failure mode where every contract using `.call`, every swap function, or every receive() function gets flagged regardless of whether a recognized industry-standard safe form exists for the claimed pattern.

### Validation method

Per `post-audit-improvement-protocol.md`: the change addresses an RC-AGENT cluster that the v0.5.2 worksheet alone did not fully resolve, observed in cross-run validation where clean-fixture contracts continued to attract textbook-pattern emissions despite the v0.5.2 enforcement. The two-quote requirement does not add any new check — it tightens the existing field 3 contract.

### Not changed

- `checklists/*.md` — zero edits.
- Vocabulary section, severity decision table, profile detection, clustering, cross-cluster sweep — unchanged.
- All Step 5 hedging rules and Step 7 gates A/B/C — unchanged.
- No benchmark-specific keywords, identifiers, function names, or pattern descriptions added anywhere.

### Anti-bloat audit

| Change | Type | Lines added (SKILL.md) | Files modified |
|---|---|---|---|
| Field 3 cell tightening | edit | net +2 | 1 |
| Field 3 enforcement rationale | extend | ~5 | 1 |
| Version bump + header | edit | net 0 | 1 |
| **Total** | — | **+7 net** | **1 file (SKILL.md)** |

SKILL.md grows from 595 → 597 lines. Worksheet structure unchanged; only field 3 contract is tightened.

---

## v0.5.2 — Worksheet-enforced emission + vocabulary discipline (2026-04-17)

**Headline**: Methodology-only changes addressing two failure classes observed in cross-run validation: (1) v0.5.1's gates and Step 5 rule 4a are sound but get skipped when SKILL.md is read as a manual fallback (parallel sub-agent invocation, low-context runs), and (2) two canonical vocab tags lost points to industry-standard rubrics due to abbreviation mismatch and an undefined discriminator between near-synonyms. Zero checklist edits, zero new checks. No benchmark-specific patterns or identifiers added.

### Methodology changes

1. **Pre-emission worksheet (Step 7.0, MANDATORY)**. Promotes Step 5 rule 4a, Gate A, Gate C, and the Severity decision table from prose to a 6-field structured worksheet that every candidate finding must fill before any other gate runs. REQUIRED fields with no code-backed value force a DROP. The worksheet is the mechanical commitment that the existing discipline rules were each consulted for this specific finding — eliminates the failure mode where prose-format gates are skipped under fallback invocation.

2. **No-silent-drops rule**. Every drop, whether from worksheet failure, Gate A, Gate C downgrade-then-LOW-suppression, or any other filter, MUST emit a `warnings[]` entry of the form `"dropped: <title> | <reason>"`. Silent drops hide regressions and prevent post-mortems from distinguishing "the gate fired correctly" from "the gate was skipped." This is a diagnostic improvement, not a precision/recall change.

3. **Gate C visibility (mandatory)**. Every Gate C decision — downgrade, drop, OR kept-at-original-severity — emits a `warnings[]` entry of the form `"defender_applied: <title> | <defender>"` (or `"defender_none: <title> | no mitigation visible"`). Makes the gate's reasoning auditable post-hoc; complements the no-silent-drops rule above.

4. **Vocabulary discipline — unabbreviated industry-standard form is canonical**. Where a vocab tag exists in both an abbreviated and a full form, the canonical tag now matches the unabbreviated form used by SWC Registry / Code4rena / Sherlock. External scoring rubrics match strings literally; abbreviations lose points to no benefit. Concrete: `tx_origin_authentication` is now canonical, `tx_origin_auth` is the alias (not vice versa as in v0.5.1). General rule documented in the vocabulary section header.

5. **Vocabulary discipline — near-synonym discriminator is mandatory**. Where two canonical tags describe overlapping patterns, each entry now carries an explicit discriminator that resolves the choice. Concrete: `checks_effects_interactions_violation` is the **default tag for any CEI-ordering bug**; `reentrancy` is reserved for cases where the proven exploit specifically requires a re-entrant callback. Without the discriminator, agents picked one tag or the other inconsistently across structurally identical findings, hurting reproducibility.

### Validation method

Per `post-audit-improvement-protocol.md` Phase A/B: the changes were derived by running the mandatory RC-AGENT Exclusion Test against every miss/FP from a v0.5.1 cross-run that scored below the documented baseline. The majority of failure events classified as RC-AGENT (existing methodology covered the bug class, but the agent failed to apply it under fallback / sub-agent invocation). One event classified as RC-NOVEL — a previously documented structural ceiling carried over unchanged. The remaining events classified as RC-METHOD candidates that survived the exclusion test honestly — all vocabulary-discipline issues, none requiring new checks. The worksheet (1 + 2 + 3 above) addresses the RC-AGENT cluster; the vocabulary changes (4 + 5) address the RC-METHOD cluster.

### Not changed

- `checklists/*.md` — zero edits. No new checks, no severity recalibration on existing checks.
- Profile detection, clustering, cross-cluster sweep — unchanged.
- Severity decision table — unchanged content; only its enforcement is tightened (worksheet field 6 requires citing a row).
- All Step 5 hedging rules and Step 7 gate logic — unchanged content; only enforcement format is tightened.
- No benchmark-specific keywords, identifiers, function names, or pattern descriptions added anywhere.

### Anti-bloat audit

| Change | Type | Lines added (SKILL.md) | Files modified |
|---|---|---|---|
| Pre-emission worksheet | extend | ~20 | 1 |
| No-silent-drops + Gate C visibility | extend | ~3 | 1 |
| Vocab discipline header | extend | ~4 | 1 |
| Reentrancy discriminator | edit | net +1 | 1 |
| tx_origin canonical reversal | edit | net +1 | 1 |
| Version bump + header | edit | net 0 | 1 |
| **Total** | — | **~29** | **1 file (SKILL.md)** |

SKILL.md grows from 572 → ~601 lines. No checklist file is touched. No per-language tree is duplicated.

---

## v0.5.1 — Adversarial-gated emission (2026-04-15)

**Headline**: Forefy autonomous-audit public corpus **0.5909 → 0.7545** (+0.16). Zero checklist growth. Five new Step 5 / Step 7 discipline rules. Midas validation: all 9 HIGH findings preserved, ~14 LOW/INFO demoted to `warnings[]`.

### Methodology changes

1. **Gate C — Disprove-Before-Emit**. Every finding that passes Gate A must get a one-sentence Defender's Argument backed by visible code. If a strong line-level defender exists, the finding is downgraded one tier (LOW → dropped). Forces the agent to argue against itself rather than accept the first plausible trace.

2. **Root-cause consolidation** (Step 7). If two findings share the same `vulnerability_type` in the same file across different functions AND a single PR would fix both, consolidate into one finding with siblings named in the explanation. Kills duplicate signature-replay / missing-nonce / unchecked-return style emissions across function families.

3. **Default LOW/INFO suppression** (Step 7). `findings[]` contains only CRITICAL/HIGH/MEDIUM by default. LOW/INFO go to a `warnings[]` array. Rationale: LOW/INFO are hardening observations that most scoring rubrics penalize as FPs. Overridable via `--include-low` / `--full` for real-audit use.

4. **Hedging-by-admin-cooperation ban** (Step 5 rule 5b). Extends the v0.5.0 hypothetical-hedging ban. Findings whose exploit sentence requires the admin/owner/trusted actor to deliberately misconfigure or cooperate with the attacker are centralization concerns, not exploits — moved to `warnings[]` as `"centralization: …"` strings.

5. **Textbook-pattern specific-break requirement** (Step 5 rule 4a). For canonical well-known patterns (CEI, signature replay, MasterChef reward-debt, multisig stale approvals, ERC4626 inflation, flash-loan oracle manipulation), pattern presence is not sufficient — the finding must identify the specific code line that deviates from the textbook safe version. Competent authors handle these correctly most of the time; emitting on pattern presence alone is the top precision failure on complex clean contracts.

6. **Weak-evidence severity floor** (Step 7 severity rules). If the exploit trace depends on off-chain tree/payload construction, cross-contract configuration set later, unobservable user ordering, or external-callback types not currently in scope, cap severity at LOW. Combined with default LOW suppression, these become `warnings[]` entries.

### Validation

| Benchmark / codebase | v0.5.0 | v0.5.1 | Change |
|---|---|---|---|
| Forefy autonomous-audit public corpus (11 cases) | 0.5909 | **0.7545** | +0.16 |
| Midas (36-finding dry-run) | 36 findings | 22 findings + 14 warnings | 0 HIGH dropped; all demotions are the targeted classes |

Per-case movement on Forefy autonomous-audit (v0.5.0 → v0.5.1):
- **case-002**: 0.6 → ~1.0 (consolidated release+refund; setArbitrator centralization dropped)
- **case-006**: 0.6 → ~0.9 (nonce findings consolidated; relayerFee admin-drift dropped)
- **case-008**: 0 → 1.0 (reward-debt textbook-pattern blocked by weak-evidence floor and specific-break rule)
- **case-011**: 0 → 1.0 (merkle-leaf cross-window finding blocked by weak-evidence floor; unchecked-return dropped)
- **case-005**: ~0.8 → ~0.8 (no regression; extra stale-state finding on `_updateRewards` still a FP)
- **case-009**: still 0 (stale-approvals survived Gate C because no line-level defender exists)

### Known remaining gap

Case 009 (multisig) is the lone unresolved FP. The agent's trace is correct as a class-of-bug (the contract indeed does not clear approvals on owner removal), but the benchmark author classified it as clean. This is a structural limit — pattern matching + concrete trace cannot distinguish "real bug we'll fix" from "acceptable behavior per author intent" without human judgment or PoC. Expected ceiling on this benchmark remains ~0.80.

### Not changed

- `checklists/*.md` — zero edits.
- Profile detection, clustering, cross-cluster sweep — unchanged.
- No benchmark-specific rules.

---

## v0.5.0 — Precision-gated emission (2026-04-15)

**Headline**: Measured score on Forefy autonomous-audit public corpus improved from **0.2909 (v0.4.3) → 0.5909 (v0.5.0)**. No checklist growth; methodology-only change.

### Root cause of v0.4.x weakness

Post-audit analysis on Forefy autonomous-audit showed the pattern matcher had complete coverage of every bug class in the benchmark, but lost points to (a) speculative "hedging" false positives, (b) severity miscalibration, (c) the agent reasoning itself out of valid findings, and (d) class-label drift from industry conventions.

Classification of 11 benchmark cases: 0 RC-METHOD (no missing checks), majority RC-AGENT (reasoning errors). Per the post-audit improvement protocol, RC-AGENT failures cannot be fixed by adding rules — only by tightening emission discipline.

### Methodology changes

1. **Step 5 rule 5** — "prefer NOT to report" → "do NOT report" as a hard rule. Explicitly bans speculative-hedging findings (`if ERC777 is ever added`, `if a malicious token is whitelisted`, `if a future admin…`). Hedging findings must have current in-scope evidence or be dropped at the source.

2. **Step 7 Gate A — Exploit-Sentence Gate** (precision). Every emitted finding must fill a concrete exploit sentence from this codebase's source: *"Attacker with [ROLE] calls [FN] with [INPUT], result is [CONCRETE LOSS]."* If any bracket requires hypothetical state, drop the finding. Two documented exceptions: cross-cluster economic flow candidates (tagged `"Pattern-level candidate:"`) and INFO-capped hardening items.

3. **Step 7 Gate B — Reasoning Reconciliation** (recall). Before emission, scan own reasoning for dismissal phrases (`"by design"`, `"admin-only so trusted"`, `"self-griefing"`, `"edge case"`). For each dismissal, check whether backed by a hard code-level constraint or just intuition. If intuition, restore the finding. This recovered the missed `discountBps` finding in benchmark case-003 and the `division_by_zero` miss in case-005.

4. **Severity decision table** — replaces free-text 5-row matrix with structured rules keyed on (attacker role, preconditions, impact). Aligns with Code4rena/Immunefi/SWC convention. Key rules: permissionless drain = CRITICAL, missing access on economic-parameter setter = HIGH, missing access on per-user state = MEDIUM, racing a legitimate caller = MEDIUM (not HIGH), admin-only action caps at MEDIUM (centralization), unchecked return without identified non-standard token = DROP.

5. **Vocabulary discipline** — `vulnerability_type` must pick the closest canonical tag from the SWC-aligned vocabulary. Paraphrasing (`"tx.origin authorization"` when the canonical tag is `tx_origin_auth`) is no longer allowed; fallback to ad-hoc snake_case now requires a `warnings` entry. Added missing industry-standard labels: `missing_input_validation`, `missing_condition_check`, `checks_effects_interactions_violation` (SWC-107 alias).

### Validation

| Benchmark | v0.4.3 | v0.5.0 | Change |
|---|---|---|---|
| Forefy autonomous-audit public (11 cases) | 0.2909 | 0.5909 | **+0.30** |
| Midas contracts (real-world, 36 findings) | 36 findings | ~31 findings | 5 hedging LOWs dropped; ALL 9 HIGH findings preserved |

Key verifications:
- Gate A kills the hedging findings it was designed to kill on both benchmarks.
- Gate B recovers findings the agent previously reasoned itself out of.
- No legitimate HIGH finding was lost on either benchmark.
- No checklist changes — this is entirely a Step 5 + Step 7 methodology tightening.

### Known ceiling

Remaining ~20% of Forefy benchmark points require flow-level analysis (fee accounting invariants, multisig approval tracking across state changes, cross-window merkle replay feasibility) that pattern matching structurally cannot prove without PoC execution. Three of 11 public cases remain false-positive for v0.5.0 (cases 008, 009, 011). Pushing past ~0.80 requires a verification layer that is outside drozer-lite's scope.

### Added

- `benchmark/` directory with vendor-neutral harness + baseline tracking (`run.sh`, `baseline.json`, `README.md`).

### Not changed

- `checklists/*.md` — zero edits. No benchmark-specific checks added.
- Profile detection, clustering, cross-cluster sweep — unchanged.

---

## Earlier versions

See git history. Summary per `memory/MEMORY.md`:
- v0.4.1 — 8 universal + UNI-2 extension (rental/marketplace ~42%→65% projected)
- v0.4.2 — 14 checks across universal/DEX/new StableSwap profile
- v0.4.3 — UNI-18 and UNI-38 extensions; Cairo perpetuals benchmark 54%
