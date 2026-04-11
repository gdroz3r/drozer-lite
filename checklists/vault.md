# Vault checklist

Triggered when the source contains ERC-4626 interfaces or share-based deposit/withdraw patterns.

> **Status:** Build Phase 1 placeholder. Content ported in Build Phase 2 from the main drozer vault profile.

Categories (to be expanded):

- First depositor inflation attack (share price manipulation via donation)
- Zero-state return (convertToShares / previewDeposit returning 0 on empty vault)
- Rounding direction (rounding in favor of the attacker, not the protocol)
- Donation attack via direct ERC-20 transfer
- Share/asset mismatch in withdraw/redeem flow
- Slippage protection on user-facing deposit/withdraw
