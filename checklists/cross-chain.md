# Cross-chain checklist

Triggered when the source contains LayerZero (lzReceive), CCIP (ccipReceive), Wormhole, or bridge patterns.

> **Status:** Build Phase 1 placeholder. Content ported in Build Phase 2 from the main drozer cross-chain profile.

Categories (to be expanded):

- Message replay (missing sequence number, missing nonce)
- Trusted remote / peer verification (unset peer, address-vs-eoa confusion)
- Source chain verification (chainId spoofing)
- Failure handling (silent failures, lost messages, retry loops)
- Sender attribution (msg.sender = endpoint vs original sender)
- Gas escrow / refund path safety
