---
name: insumer-trust
description: >
  InsumerAPI wallet trust profile: a curated multi-dimensional condition-based
  access bundle for a single wallet. 155 base checks across 27 chains in 10
  dimensions (stablecoins, governance, NFTs, staking, institutional
  stablecoins, tokenized treasuries, stablecoin deposits, wrapped bitcoin,
  names, account), plus optional Solana, XRPL, Bitcoin and Tron dimensions (up
  to 176 checks across 29 chains in 14 dimensions). Use when the user wants an InsumerAPI
  trust profile, a pre-built signed wallet snapshot rather than conditions
  specified one by one (for example an InsumerAPI pre-transaction trust check). The profile is signed once, as a whole. Carry it unchanged:
  never re-sign or wrap it.
metadata:
  version: "0.3.0"
  author: InsumerAPI
---

# InsumerAPI Wallet Trust Profile

A curated condition bundle for a single wallet. Same primitive as `insumer-attest` (read → evaluate → sign), but the conditions are pre-defined: 155 base checks across 27 chains in 10 dimensions, with optional cross-chain extensions. **Boolean, not balance, on every check.** Every row is a presence check.

Pick this skill when the developer wants a snapshot. Pick `insumer-attest` when they want to specify their own conditions.

## What you get

- **155 base checks** across **27 chains** in **10 dimensions** (23 EVM chains plus the Solana, XRPL, Stellar and Sui rows inside the base dimensions):
  - **Stablecoins** (52): USDC, USDT, OUSD, PYUSD, USDG, USD1, RLUSD, USDS, DAI and EURC across 23 EVM chains, including USDC on Arc and USDG on Robinhood Chain
  - **Governance** (8): UNI, AAVE, ENS, LDO, SKY and COMP on Ethereum, ARB on Arbitrum, OP on Optimism
  - **NFTs** (3): BAYC, Pudgy Penguins, Wrapped CryptoPunks
  - **Staking** (5): stETH, rETH, cbETH, wstETH, weETH
  - **Institutional stablecoins** (8): EURCV, USDCV, USDC, and BENJI across Ethereum, Solana, XRPL, Stellar, and Sui. Always present; the Solana, XRPL, Stellar and Sui entries are evaluated only when the matching wallet is supplied, and are otherwise marked `evaluated: false`
  - **Tokenized treasuries** (16): BUIDL, USYC, OUSG, USTB, USDY (the USDY on Sui row needs `suiWallet`, otherwise `evaluated: false`)
  - **Stablecoin deposits** (39): Aave v3 aUSDC/aUSDT, sUSDS, sDAI, listed Morpho USDC vaults
  - **Wrapped bitcoin** (12): cbBTC, WBTC, tBTC
  - **Names** (2): ENS .eth, Basenames
  - **Account** (10): two rows per chain on Ethereum, Base, Arbitrum, Optimism and Polygon. "Contract code on X" is met when bytecode other than the EIP-7702 delegation designator is at the wallet address; "EIP-7702 delegation on X" is met when the designator is there. The two are exclusive per chain; a plain key account reads false on both. Which contract is never named; to require a specific delegation target, send `delegate` with an `account_code` condition in `insumer-attest` (the answer is still yes or no). Each row's `evaluatedCondition` is `{type: "account_code", chainId, expect, operator: "code_state"}`, hashed exactly like the equivalent attest condition
- **Optional extensions** (when extra wallet addresses are provided):
  - **Solana** (14): pass `solanaWallet` (USDC, EURC, OUSD, PYUSD, USD1, USDG, USDS, BUIDL, USDY, WBTC, cbBTC, tBTC, JitoSOL, mSOL on Solana)
  - **XRPL** (3): pass `xrplWallet` (RLUSD, USDC, OUSG)
  - **Bitcoin** (1): pass `bitcoinWallet` (native BTC)
  - **Tron** (3): pass `tronWallet` (USDT, USD1, WBTC)
  - **Stellar / Sui**: pass `stellarWallet` / `suiWallet`. These add no checks and no dimension; they let the Stellar and Sui rows inside the base dimensions be evaluated
- Up to 176 total checks across 29 chains in 14 dimensions when all extensions are included
- Each check returns its own boolean; the response includes per-dimension and overall summaries
- Dimension order is fixed: the base dimensions in the order above (`stablecoins`, `governance`, `nfts`, `staking`, `institutional_stablecoins`, `tokenized_treasuries`, `stablecoin_deposits`, `wrapped_bitcoin`, `names`, `account`), then whichever of `solana`, `xrpl`, `bitcoin`, `tron` were switched on, in that order
- `conditionSetVersion` is a dated set id (currently `"2026-10-08"`), the same on every key version, signed with the profile. It names the check list that was run: log it, never reject on it
- 3 credits standard, 6 credits with `proof: "merkle"`

## Architectural property to preserve

The whole trust profile is signed once by InsumerAPI: one `sig` under `kid: insumer-trust-v2` (plus the post-quantum companion `pqSig` / `pqKid`) covers the entire `trust` object. There are no per-dimension or per-check signatures. **Do not add an orchestrator-layer wrap.** If you build a multi-issuer trust envelope that includes this profile, carry the signed object exactly as issued, beside the other issuers' signed objects, and never re-sign it or wrap it under a new envelope signature. Verifiers should be able to check InsumerAPI's signature directly against its JWKS.

## Setup

```bash
export INSUMER_API_KEY='insr_live_...'
```

## Reference values

- **Endpoint**: `POST https://api.insumermodel.com/v1/trust`
- **Cost**: 3 credits standard, 6 credits with `proof: "merkle"`
- **Wallet pattern**: `wallet` is required (EVM, `0x` + 40 hex chars). `solanaWallet`, `xrplWallet`, `bitcoinWallet`, `tronWallet`, `stellarWallet` (G-address) and `suiWallet` (`0x` + 64 hex chars) are optional add-ons.
- **Trust profile ID format**: `TRST-XXXXX` (returned in `data.trust.id`)

## Usage

### Example 1: EVM-only profile

```bash
curl -X POST https://api.insumermodel.com/v1/trust \
  -H "X-API-Key: $INSUMER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet": "0x1601843c5E9bC251A3272907010AFa41Fa18347E"
  }'
```

Response shape (abbreviated; the counts are from a real profile of this wallet, a contract on all five account chains):

```json
{
  "ok": true,
  "data": {
    "trust": {
      "id": "TRST-81224",
      "wallet": "0x1601843c5E9bC251A3272907010AFa41Fa18347E",
      "conditionSetVersion": "2026-10-08",
      "dimensions": {
        "stablecoins":               { "checks": [...], "passCount": 6, "failCount": 46, "notEvaluatedCount": 0, "total": 52 },
        "governance":                { "checks": [...], "passCount": 0, "failCount": 8,  "notEvaluatedCount": 0, "total": 8 },
        "nfts":                      { "checks": [...], "passCount": 0, "failCount": 3,  "notEvaluatedCount": 0, "total": 3 },
        "staking":                   { "checks": [...], "passCount": 0, "failCount": 5,  "notEvaluatedCount": 0, "total": 5 },
        "institutional_stablecoins": { "checks": [...], "passCount": 0, "failCount": 2,  "notEvaluatedCount": 6, "total": 8 },
        "tokenized_treasuries":      { "checks": [...], "passCount": 0, "failCount": 15, "notEvaluatedCount": 1, "total": 16 },
        "stablecoin_deposits":       { "checks": [...], "passCount": 5, "failCount": 34, "notEvaluatedCount": 0, "total": 39 },
        "wrapped_bitcoin":           { "checks": [...], "passCount": 0, "failCount": 12, "notEvaluatedCount": 0, "total": 12 },
        "names":                     { "checks": [...], "passCount": 0, "failCount": 2,  "notEvaluatedCount": 0, "total": 2 },
        "account":                   { "checks": [...], "passCount": 5, "failCount": 5,  "notEvaluatedCount": 0, "total": 10 }
      },
      "summary": { "totalChecks": 155, "totalPassed": 16, "totalFailed": 132, "totalNotEvaluated": 7, "dimensionsWithActivity": 3, "dimensionsChecked": 10 },
      "profiledAt": "2026-10-07T21:53:04.795Z",
      "expiresAt": "2026-10-07T22:23:04.795Z"
    },
    "sig": "...",
    "kid": "insumer-trust-v2",
    "pqSig": "...",
    "pqKid": "insumer-trust-pq1"
  },
  "meta": {
    "creditsRemaining": ...,
    "creditsCharged": 3
  }
}
```

The first two `account` rows of that profile, as signed:

```json
{"label":"Contract code on Ethereum","chainId":1,"met":true,"evaluatedCondition":{"type":"account_code","chainId":1,"expect":"contract","operator":"code_state"},"conditionHash":"0xfd7b6aa42eb012184fa54d9d5d99c6ab18481e0ce33ec0ec0e9d28d37b54ccbc","blockNumber":"0x18eea5a","blockTimestamp":"2026-10-07T21:52:59.000Z"}
{"label":"EIP-7702 delegation on Ethereum","chainId":1,"met":false,"evaluatedCondition":{"type":"account_code","chainId":1,"expect":"eip7702","operator":"code_state"},"conditionHash":"0xdef6fadcef95f59f4621fa2bf788e6be0ffc0492dba22038999b8cd757adf18b","blockNumber":"0x18eea5a","blockTimestamp":"2026-10-07T21:52:59.000Z"}
```

### Example 2: With Solana USDC

```bash
curl -X POST https://api.insumermodel.com/v1/trust \
  -H "X-API-Key: $INSUMER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "solanaWallet": "5xY...solanaAddress"
  }'
```

### Example 3: Multi-chain profile (EVM + Solana + XRPL + Bitcoin)

```bash
curl -X POST https://api.insumermodel.com/v1/trust \
  -H "X-API-Key: $INSUMER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "solanaWallet": "5xY...solanaAddress",
    "xrplWallet": "rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH",
    "bitcoinWallet": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
  }'
```

Each provided Solana, XRPL, Bitcoin or Tron wallet adds its dimension to the response. A Stellar or Sui wallet (`stellarWallet`, `suiWallet`) adds no dimension; it lets the matching institutional-stablecoin entries be evaluated instead of marked `evaluated: false`.

### Example 4: Merkle proofs (advanced)

```bash
curl -X POST https://api.insumermodel.com/v1/trust \
  -H "X-API-Key: $INSUMER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "proof": "merkle"
  }'
```

An EVM token row carries an EIP-1186 storage proof when its balance slot can be discovered. Computed-balance rows (Aave aTokens, BUIDL), rows with non-standard storage layouts, and rows on chains that serve no proofs are declined with a reason; NFT and non-EVM rows are declined; `account` rows carry `proof.available: false` with a reason pointing at `/v1/attest`, where an `account_code` condition in proof mode carries the account proof; unevaluated checks carry no proof key. **Costs 6 credits** instead of 3; the premium is refunded whenever no proof could be delivered. Proofs reveal raw on-chain balances. Only opt in if the consumer explicitly needs the raw balances.

## When to use trust profile vs. custom attest

| User asks for... | Use |
|---|---|
| "Verify this wallet holds X on chain Y" | `insumer-attest` |
| "Gate by USDC balance on Base" | `insumer-attest` |
| "Pre-transaction trust check" | `insumer-trust` |
| "Show me what this wallet holds across chains" | `insumer-trust` |
| "Multi-dimensional wallet profile" | `insumer-trust` |
| "Should I transact with this wallet" | `insumer-trust` |

For multiple wallets in one call, use `insumer-trust-batch`.

## Code emission rules

1. **Read the API key from an env var.** Never inline.
2. **Verify the signature offline.** Use `insumer-jwks-verify`. The signed boolean(s) is the product.
3. **Don't re-sign or wrap the profile.** One InsumerAPI signature covers the whole `trust` object; placing it under a new envelope signature defeats the verification chain. A check whose wallet was not supplied is marked `evaluated: false` and counted in `totalNotEvaluated`, never as a failure.
4. **Don't cache the verdict.** Cache the JWKS, not the trust profile result. Wallet state changes.
5. **Backend only.** The API key is a backend credential.

## Helper script

`scripts/trust.py` — Python helper that wraps `POST /v1/trust`. Reads `INSUMER_API_KEY` from env, accepts `--wallet`, `--solana`, `--xrpl`, `--bitcoin`, `--tron`, `--stellar`, `--sui`, `--proof merkle`.

```bash
python scripts/trust.py --wallet 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
```

## Error handling

| Status | Cause | Fix |
|---|---|---|
| `400` | Missing `wallet` or invalid format | EVM wallet `^0x[a-fA-F0-9]{40}$` is required |
| `401` | Missing/invalid API key | See `insumer-auth` |
| `402` | Out of credits | Top up via Path 4 in `insumer-auth` |
| `503` | Upstream blockchain data source unavailable | Retryable; no credits charged |

A `503` carries error code `rpc_failure`. It means a read did not complete and nothing was signed. It is never a `false`: do not report it as a check that was not held. Retry the call.

## Related skills

| Skill | Purpose |
|---|---|
| `insumer-auth` | API key creation, top-up |
| `insumer-attest` | Custom condition (pick this if not using the curated bundle) |
| `insumer-trust-batch` | Same primitive for multiple wallets in one call |
| `insumer-jwks-verify` | Offline ES256 verification |

## References

- [InsumerAPI OpenAPI spec](https://insumermodel.com/openapi.yaml)
- [Public JWKS](https://insumermodel.com/.well-known/jwks.json)
- [Developer docs — trust profile](https://insumermodel.com/developers/trust/)
