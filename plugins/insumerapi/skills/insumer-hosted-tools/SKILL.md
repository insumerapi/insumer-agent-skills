---
name: insumer-hosted-tools
description: >
  How to use the InsumerAPI MCP tools this plugin connects to (the hosted
  server at api.insumermodel.com/mcp, no key needed). Use when the user asks
  to check if a wallet holds a token or an amount, whether a wallet owns an
  NFT, whether a wallet is a registered ERC-8004 agent, for a wallet trust
  profile, for InsumerAPI's signing keys or how to verify an attestation, for
  compliance templates, or for a merchant's discount, and the insumer MCP
  tools are available. Do not use for exact balances, prices, or sending
  transactions. Explains the shared daily allowance and when to switch to the
  REST skills with the user's own key.
metadata:
  version: "0.1.1"
  author: InsumerAPI
---

# InsumerAPI hosted tools

This plugin connects to InsumerAPI's hosted MCP server. The tools need no account and no key. Prefer them over the REST path in the other skills whenever they are available; the REST skills remain the reference for request shapes, response fields and verification.

**Boolean, not balance.** Every signed result says whether a wallet satisfies a condition right now. It never says how much the wallet holds.

## The ten tools

| Tool | What it does | Spends the allowance? |
| ---- | ------------ | --------------------- |
| `insumer_jwks` | The public signing keys: an ECDSA P-256 key under its kids, then the ML-DSA-65 post-quantum key | No |
| `insumer_attest` | Signed yes or no for 1 to 10 conditions on one wallet, across 37 chains | Yes |
| `insumer_compliance_templates` | Named EAS templates (Coinbase Verifications, Gitcoin Passport) usable as conditions | No |
| `insumer_wallet_trust` | Signed trust profile for one EVM wallet: 155 base checks across 27 chains in ten dimensions, held or not held, no score | Yes |
| `insumer_batch_wallet_trust` | Trust profiles for up to 10 wallets in one call | Yes, per wallet |
| `insumer_list_merchants` | The public merchant directory | No |
| `insumer_get_merchant` | One merchant's public profile: token tiers, NFT collections, discount mode | No |
| `insumer_list_tokens` | Registered tokens and NFT collections | No |
| `insumer_check_discount` | What discount a wallet would get at a merchant | No |
| `insumer_validate_code` | Whether an INSR-XXXXX discount code is valid | No |

## Rules for calling them

- **Quantities are decimal strings in display units.** `threshold: "100"` means 100 tokens, not base units. Never send `decimals`; the token's own decimals are read from the chain.
- **Chains.** EVM chains by numeric chain ID (1 Ethereum, 8453 Base, 137 Polygon, 42161 Arbitrum, 10 Optimism, 56 BNB Chain, and so on). Non-EVM by name: `solana`, `xrpl`, `bitcoin`, `tron`, `stellar`, `sui`. Each non-EVM chain needs its own wallet field (`solanaWallet`, `xrplWallet`, `bitcoinWallet`, `tronWallet`, `stellarWallet`, `suiWallet`).
- **Native coins.** `contractAddress: "native"` on every chain except Sui, where native SUI is the coin type `0x2::sui::SUI`.
- **NFTs** need the NFT contract address; `native` with `nft_ownership` is rejected.
- **Read the result, not the request.** Report `met` per condition and the overall `pass`. Quote the attestation ID, the `kid` and `pqKid`, and the block or ledger it was read at. Do not invent a balance; none is returned.
- **Verification.** Anyone can check a result offline with the `insumer-verify` package (npm and PyPI) against the keys from `insumer_jwks`. Match keys by `kid`, never by position. The `insumer-jwks-verify` skill has the details.

## The shared allowance

The hosted server runs on one shared allowance for the tools that produce signed results (`insumer_attest`, `insumer_wallet_trust`, `insumer_batch_wallet_trust`). When it is used up for the day, those tools return an error that says so; it resets at 00:00 UTC. The free tools keep working.

When that happens, or when the user needs more than occasional calls, key and credit management, or the merchant tools:

1. Tell the user plainly that the shared allowance is used up for today.
2. Offer the user's own free key: the `insumer-auth` skill creates one with an email address (10 verifications plus 100 requests a day, no card), and the `insumer-attest`, `insumer-trust` and `insumer-trust-batch` skills call the REST API with it.
3. Never ask the user to paste an API key into the chat for use with the hosted tools. The hosted tools take no key. A key belongs in the user's own environment, as the REST skills describe.

## What not to claim

- InsumerAPI does not score, rank or vet wallets. A trust profile lists what is held and what is not.
- Registration as an ERC-8004 agent is permissionless minting; a `met: true` there means registered, not vetted.
- A signed `false` is a verdict, not an error. An error is a response with `ok: false`.
- InsumerAPI stores no wallet addresses or conditions from verification requests. Say so only in those words; do not expand on how the service works internally.

## Related skills

- `insumer-attest`, `insumer-trust`, `insumer-trust-batch`: the same operations over REST with the user's own key, with the full request and response shapes.
- `insumer-auth`: getting and topping up a key.
- `insumer-discount`: a signed discount code at an InsumerAPI merchant, over REST with the user's own key.
- `insumer-jwks-verify`: verifying any signed response offline.
