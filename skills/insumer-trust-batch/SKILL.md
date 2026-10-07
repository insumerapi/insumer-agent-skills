---
name: insumer-trust-batch
description: >
  InsumerAPI batch wallet trust profiles: the same curated bundle as
  insumer-trust, for up to 10 wallets in a single call. Use when the user wants
  InsumerAPI trust profiles for a list of wallets (for example screening an
  airdrop or allowlist with InsumerAPI). Each wallet's profile is independently
  signed; the response supports partial success.
metadata:
  version: "0.3.0"
  author: InsumerAPI
---

# InsumerAPI Batch Wallet Trust Profile

Same curated condition-based access bundle as `insumer-trust`, but accepts up to **10 wallets** in one request. Each wallet's profile is independently signed; the response supports partial success — failures for one wallet don't fail the rest.

Each wallet's profile is signed once, as a whole, by InsumerAPI (`kid: insumer-trust-v2`, with the post-quantum companion). There are no per-dimension signatures and no signature over the batch. **Do not add an orchestrator wrap:** carry each signed profile exactly as issued.

## Setup

```bash
export INSUMER_API_KEY='insr_live_...'
```

## Reference values

- **Endpoint**: `POST https://api.insumermodel.com/v1/trust/batch`
- **Cost**: 3 credits per **successful** wallet (6 with `proof: "merkle"`). Failed wallets in the batch don't cost credits.
- **Max wallets per call**: 10
- **Profile ID format per wallet**: `TRST-XXXXX`

## Request shape

`wallets` is an **array of objects**, each with a required `wallet` field plus optional cross-chain wallet fields. (Not an array of plain strings.)

```json
{
  "wallets": [
    { "wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045" },
    {
      "wallet": "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",
      "solanaWallet": "5v9CXTpN3WHbM2jAYty88qDGz7P4yuMv8fnuPRXBPmiB"
    }
  ]
}
```

| Field per entry | Required | Notes |
|---|---|---|
| `wallet` | yes | EVM address, `0x` + 40 hex chars |
| `solanaWallet` | optional | Adds the 14-check `solana` dimension to this wallet's profile and evaluates the Solana rows in institutional stablecoins |
| `xrplWallet` | optional | Adds the `xrpl` dimension (RLUSD, USDC, OUSG) and evaluates the XRPL row in institutional stablecoins |
| `bitcoinWallet` | optional | Adds the `bitcoin` dimension (native BTC) |
| `tronWallet` | optional | Adds the `tron` dimension (USDT, USD1, WBTC) |
| `stellarWallet` | optional | Evaluates the Stellar rows in the institutional stablecoins dimension; adds no dimension |
| `suiWallet` | optional | Evaluates the Sui rows (USDC in institutional stablecoins, USDY in tokenized treasuries); adds no dimension |

Top-level `proof: "merkle"` (optional) applies to all wallets in the batch and costs 6 credits per wallet.

## Response shape

```json
{
  "ok": true,
  "data": {
    "results": [
      {
        "trust": {
          "id": "TRST-A1B2C",
          "wallet": "0xd8dA...",
          "conditionSetVersion": "2026-10",
          "dimensions": { ... },
          "summary": { "totalChecks": 145, "totalPassed": 7, "totalFailed": 131, "totalNotEvaluated": 7, ... },
          "profiledAt": "2026-...",
          "expiresAt": "2026-..."
        },
        "sig": "...",
        "kid": "insumer-trust-v2",
        "pqSig": "...",
        "pqKid": "insumer-trust-pq1"
      },
      {
        "trust": { "id": "TRST-D4E5F", "wallet": "0xAb58...", ... },
        "sig": "...",
        "kid": "insumer-trust-v2",
        "pqSig": "...",
        "pqKid": "insumer-trust-pq1"
      }
    ],
    "summary": { "requested": 2, "succeeded": 2, "failed": 0 }
  },
  "meta": {
    "creditsCharged": 6,
    "creditsRemaining": ...
  }
}
```

Each entry in `data.results[]` is **either** a `{trust, sig, kid, pqSig, pqKid}` object **or** `{error: { wallet, message }}`. Iterate, branch, and verify each `trust` independently with `insumer-jwks-verify`.

## Usage

### Example 1: Two EVM wallets

```bash
curl -X POST https://api.insumermodel.com/v1/trust/batch \
  -H "X-API-Key: $INSUMER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallets": [
      { "wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045" },
      { "wallet": "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B" }
    ]
  }'
```

### Example 2: Mixed cross-chain coverage per wallet

```bash
curl -X POST https://api.insumermodel.com/v1/trust/batch \
  -H "X-API-Key: $INSUMER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallets": [
      {
        "wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        "solanaWallet": "5v9CXTpN3WHbM2jAYty88qDGz7P4yuMv8fnuPRXBPmiB"
      },
      {
        "wallet": "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",
        "xrplWallet": "rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH",
        "bitcoinWallet": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
      }
    ]
  }'
```

### Example 3: Batch with Merkle proofs

```bash
curl -X POST https://api.insumermodel.com/v1/trust/batch \
  -H "X-API-Key: $INSUMER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallets": [
      { "wallet": "0x..." },
      { "wallet": "0x..." }
    ],
    "proof": "merkle"
  }'
```

Cost: up to `successful_wallets * 6` credits; a wallet whose profile carried no proof costs 3. Reveals raw on-chain balances — only opt in if needed.

## When to use batch vs single

| Situation | Use |
|---|---|
| Single wallet | `insumer-trust` |
| 2–10 wallets, same call | `insumer-trust-batch` |
| More than 10 wallets | Loop over batches of 10 |
| Different conditions per wallet | Loop over `insumer-attest` (custom conditions) |
| Same custom conditions for many wallets | Loop over `insumer-attest` |

## Code emission rules

1. **Read the API key from an env var.** Never inline.
2. **Iterate `data.results[]` and branch on `trust` vs `error`.** Don't assume every entry succeeded.
3. **Verify each profile's signature independently.** The batch wrapper does not produce an aggregate signature; each entry in `data.results[]` carries its own `sig` and `kid`.
4. **Cap at 10 wallets per call.** For larger lists, batch client-side.
5. **Pre-validate wallet format** before sending. Invalid `wallet` formats fail validation for the entire request.
6. **Backend only.** The API key is a backend credential.
7. **Don't cache the verdict.** Wallet state changes.

## Helper script

`scripts/trust_batch.py` — Python helper. Reads `INSUMER_API_KEY` from env, accepts a wallet list via `--wallets-file` (one EVM address per line) or `--wallets w1,w2,w3`. Builds the proper array-of-objects request body.

```bash
python scripts/trust_batch.py --wallets-file allowlist.txt
```

The script prints a summary per wallet (profile ID, held / not held / not evaluated counts, and the checks held in each dimension) and saves the complete signed response to a JSON file named in the summary; `--out PATH` chooses the file. Read the summary to answer the user, and verify each entry of `data.results` in the saved file on the raw `sig` path (for example `verify_trust_profile` from the `insumer-verify` package, or the raw-sig instructions in `insumer-jwks-verify`). The script never overwrites a file; if it cannot save one, it prints the complete response instead, so a paid call is never lost. A full profile is tens of thousands of characters, so ten printed in full are more than an agent can read at once; `--full` prints the complete response anyway. Profiles cannot be fetched again, so keep the saved file rather than calling a second time.

For per-wallet cross-chain coverage, edit the script's `--wallets-file` to use JSON-line format (one object per line) or call the API directly with curl.

## Error handling

| Status | Cause | Fix |
|---|---|---|
| `400` | Missing `wallets`, exceeds 10, or invalid wallet format | Validate addresses; split into ≤10 batches |
| `401` | Missing/invalid API key | See `insumer-auth` |
| `402` | Insufficient credits for entire batch | Top up via Path 4 in `insumer-auth` |
| `429` | Rate limit exceeded | Slow down; check tier limits |

The batch endpoint does not answer `503` for an upstream data-source failure. A wallet whose chain reads fail is refused on its own: it appears as an `{error: {wallet, message}}` entry in `data.results[]` of a `200` response, is never signed, and does not consume credits. Such an entry is never a `false`: it says the wallet was not read, not that it holds nothing. Retry those wallets later.

## Related skills

| Skill | Purpose |
|---|---|
| `insumer-auth` | API key creation, top-up |
| `insumer-trust` | Single-wallet curated profile |
| `insumer-attest` | Custom condition (single call, up to 10 conditions) |
| `insumer-jwks-verify` | Offline ES256 verification — apply per `data.results[]` entry |

## References

- [InsumerAPI OpenAPI spec](https://insumermodel.com/openapi.yaml)
- [Public JWKS](https://insumermodel.com/.well-known/jwks.json)
- [Developer docs — trust profile](https://insumermodel.com/developers/trust/)
