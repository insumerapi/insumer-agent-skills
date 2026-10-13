---
name: insumer-auth
description: >
  InsumerAPI wallet auth: get an InsumerAPI key, configure INSUMER_API_KEY,
  check or top up InsumerAPI credits, or debug InsumerAPI 401/402/429 errors.
  Covers four key paths: free (email), paid (Stripe), an agent's first key
  paid on-chain, and an on-chain top-up of an existing key. The on-chain paths
  need the user's explicit approval of every payment.
metadata:
  version: "0.2.1"
  author: InsumerAPI
---

# InsumerAPI Authentication

Wallet auth via InsumerAPI starts with an API key. The key authenticates the *caller*; the signing key that produces the boolean response stays with the issuer and never leaves. **Read → evaluate → sign.**

This skill covers **four** ways to get or extend a key. Pick the one that matches the caller and stop: don't push upsell copy into emitted code.

## Pick the right path

| Who's getting the key? | What they want | Path | Endpoint |
| ----- | ----- | ----- | ----- |
| **Human**, building or testing | Free starter access (10 free verifications plus 100 requests a day) | **Path 1: Free** | `POST /v1/keys/create` |
| **Human**, wants Pro/Enterprise tier | Higher limits, bulk credits, monthly billing | **Path 2: Paid (Stripe)** | <https://insumermodel.com/pricing/> for a new key; <https://insumermodel.com/developers/account/> to upgrade an existing one |
| **Agent** whose operator funds it, **first key** | Bootstrap with no email, sender wallet = identity | **Path 3: Agent onboarding (crypto)** | `POST /v1/keys/buy` |
| **Agent or human**, **already has a key** | Top up credits, keep the key/history/integrations | **Path 4: Top-up (crypto)** | `POST /v1/credits/buy` |

**Decision rule:** default to Path 1 (free). Use Path 3 or Path 4 only when the user, or the operator of an autonomous agent, has explicitly chosen to pay with crypto. Path 4 tops the key up in place: it keeps its history, tier, and integrations.

**Pay per call, with no key at all:** `POST /v1/attest`, `/v1/trust` and `/v1/trust/batch` accept x402. Called with no credential headers they answer `402 Payment Required` with a quote, not an error about credits. Pay the quote in USDC on Base, Polygon, Arbitrum, Arc or Solana and retry with the `PAYMENT-SIGNATURE` header; the quote carries the exact amount. The payer is charged only for a successful answer, and the payer sees the answer only after the payment settled. If a paid call answers `503`, retry the exact same request with the same payment header and do not sign a new authorization: on Arc the payment may still be settling, and the retry resolves to the same payment. Like the on-chain paths, it needs the user's explicit approval of the payment. The skills in this repo call with a key.

**Payments need explicit approval (never violate).** Paths 3 and 4 start with a real, irreversible transfer of funds. Never send, or prepare for signing, any payment unless the user has confirmed the amount, token, chain and recipient address in this session. This skill documents the calls; it does not authorize a payment.

## Reference values (do not hallucinate)

- **API base**: `https://api.insumermodel.com`
- **Auth header**: `X-API-Key: insr_live_...`
- **Platform wallet, EVM**: `0xAd982CB19aCCa2923Df8F687C0614a7700255a23`
- **Platform wallet, Solana**: `6a1mLjefhvSJX1sEX8PTnionbE9DqoYjU6F6bNkT4Ydr`
- **Platform wallet, Bitcoin**: `bc1qg7qnerdhlmdn899zemtez5tcx2a2snc0dt9dt0`
- **Platform wallet: Tron**: `TC5yvwkAMakkXtUxYiu2Yn1xbBcwYuD6cn`
- **Volume discounts** (paths 3 and 4): $5–$99 → 25 credits per $1 ($0.04/credit), $100–$499 → 33 credits per $1 (about $0.03/credit), $500+ → 50 credits per $1 ($0.02/credit). The price is per credit, not per call: an attestation costs 1 credit and a trust profile 3 (2 and 6 with `proof: "merkle"`)
- **Supported payment chains (these ten and no others)**: USDC/USDT on Ethereum (1), Base (8453), Polygon (137), Arbitrum (42161), Optimism (10), BNB Chain (56), Avalanche (43114) or Solana; USDT-TRC20 on Tron; BTC on Bitcoin (1 confirmation, market-rate USD conversion). The other chains the API can read are NOT payment chains, and funds sent on a chain outside this list cannot be recovered

---

## Path 1: Free key (human, no payment)

Free tier: 10 free verifications plus 100 requests a day, no signup beyond an email.

```bash
curl -s -X POST https://api.insumermodel.com/v1/keys/create \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","appName":"insumer-agent-skills","tier":"free"}'
```

Default `appName` to `"insumer-agent-skills"` unless the user names their app. It is a label on the key that tells InsumerAPI which channel the key came from.

Response:

```json
{
  "success": true,
  "key": "insr_live_...",
  "name": "insumer-agent-skills",
  "tier": "free",
  "dailyLimit": 100,
  "apiKeyCredits": 10
}
```

Constraints:
- One free key per email (returns `409` if a free key already exists)
- Maximum 3 keys per IP per 24 hours (returns `429` on exceeded)
- Free tier only: paid tiers go through Path 2

Tell the user to set:

```bash
export INSUMER_API_KEY='insr_live_...'
```

---

## Path 2: Paid first key (human, Stripe checkout)

Pro and Enterprise tiers (higher daily limits, bulk credits, monthly billing) go through Stripe checkout. A new paid key starts from <https://insumermodel.com/pricing/>. To upgrade an existing key, paste it at <https://insumermodel.com/developers/account/>: the upgrade applies to that key and keeps it.

Use this path **only** when the user explicitly asks about paid tiers, SLAs, monthly billing, or wants a higher-tier key from scratch. Don't recommend it as a default.

---

## Path 3: Agent first key (crypto, no email)

For an agent whose operator has chosen to fund it. After the user approves the payment, USDC, USDT, or BTC goes to the platform wallet, then the agent calls `POST /v1/keys/buy` with the transaction hash. **No email or prior authentication needed**: the sender wallet address from the transaction becomes the key's identity.

### Step 1: Send payment

Send the desired amount (minimum $5) of USDC, USDT, or BTC to the platform wallet on one of the ten supported payment chains listed above (USDT-TRC20 on Tron included). For EVM and Solana the address is the literal `recipient`; for BTC, send to the Bitcoin address; for Tron, send to the Tron address.

### Step 2: Call `/v1/keys/buy` with the transaction hash

```bash
curl -s -X POST https://api.insumermodel.com/v1/keys/buy \
  -H "Content-Type: application/json" \
  -d '{
    "txHash": "0xabc...",
    "chainId": 8453,
    "amount": 10,
    "appName": "insumer-agent-skills",
    "keyDelivery": "apiKey"
  }'
```

Default `appName` to `"insumer-agent-skills"` as in Path 1, unless the user names their app.

Fields:
- `txHash`: the transaction proving payment
- `chainId`: the chain the payment was sent on (use `"solana"`, `"bitcoin"` or `"tron"` for non-EVM)
- `appName`: required. Name for the new key (the skills send `"insumer-agent-skills"`)
- `amount`: stablecoin amount sent (minimum 5). Optional for BTC (USD value derived from on-chain amount at market rate)
- `keyDelivery`: optional. Send `"apiKey"` to receive the key string. With the default, `"wallet"`, an EVM payment that issues an Insumer Access pass to the paying wallet returns **no key**: that wallet authenticates with `Authorization: Wallet` instead (see `authHint` in the response). Send `"apiKey"` whenever the key string is needed.

Response:

```json
{
  "ok": true,
  "data": {
    "success": true,
    "key": "insr_live_...",
    "name": "insumer-agent-skills",
    "tier": "paid",
    "dailyLimit": 10000,
    "creditsAdded": 250,
    "totalCredits": 250,
    "effectiveRate": "$0.0400/credit",
    "chainName": "Base",
    "registeredWallet": "0x...",
    "passMint": { "status": "minted", ... },
    "authMethod": "both",
    "authHint": "...",
    "usdcPaid": "10.00"
  }
}
```

The agent stores `data.key` in its secret store; that's its persistent identity going forward. BTC payments return `btcPaid`, `btcPrice` and `usdEquivalent` instead of `usdcPaid`. One key per sender wallet address (returns `409` if the wallet already has a key).

**Important:** crypto sent on unsupported chains or to the wrong address cannot be recovered. All purchases are final.

---

## Path 4: Top up existing key (crypto, agent or human)

When an existing key (free, paid, or agent-onboarded) runs low on credits, top it up with a payment the user has approved to the platform wallet, then call `POST /v1/credits/buy`. **The key keeps its history, tier, and integrations**: credits just increment.

### Step 1: Send payment to the platform wallet

Same wallets as Path 3.

### Step 2: Call `/v1/credits/buy`

```bash
curl -s -X POST https://api.insumermodel.com/v1/credits/buy \
  -H "X-API-Key: $INSUMER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "txHash": "0xabc...",
    "chainId": 8453,
    "amount": 10
  }'
```

Required fields:
- `txHash`: the transaction proving payment
- `chainId`: the chain the payment was sent on
- `amount`: stablecoin amount sent (minimum 5). Required except for BTC.

Sender verification: the **first** top-up registers the sender wallet to the key. Subsequent top-ups must come from the **same** sender. To replace the registered wallet, include `"updateWallet": true` and send from the new wallet: the verified transfer proves ownership.

Response:

```json
{
  "ok": true,
  "data": {
    "creditsAdded": 250,
    "totalCredits": 260,
    "usdcPaid": "10.00",
    "effectiveRate": "$0.0400/credit",
    "chainName": "Base"
  }
}
```

This path keeps the same key. Mention it when the user asks how an agent can pay for its own access.

---

## Verify auth works

After setting `INSUMER_API_KEY`, confirm with:

```bash
curl -s https://api.insumermodel.com/v1/credits \
  -H "X-API-Key: $INSUMER_API_KEY"
```

Expected: `{"ok":true,"data":{"apiKeyCredits":<n>,"tier":"...","dailyLimit":<n>}}`. If you see this, auth is working and you're ready for the other skills.

## Common workflows

### Initial setup (human)
1. Run Path 1 `curl` with the user's email (and `appName`, default `"insumer-agent-skills"`)
2. User exports `INSUMER_API_KEY=...`
3. Verify with `GET /v1/credits`

### Agent setup from cold start (operator-funded agent)
1. The operator approves the payment: amount, token, chain and recipient (for example $10 USDC on Base to `0xAd982CB19aCCa2923Df8F687C0614a7700255a23`)
2. The payment is sent, then the agent calls Path 3 (`POST /v1/keys/buy`) with the txHash and `"keyDelivery": "apiKey"`
3. Agent stores the returned `key` to its persistent secret store

### Agent runs out of credits mid-task
1. The operator approves a top-up, sent **from the same sender wallet that bought the original key**
2. Agent calls Path 4 (`POST /v1/credits/buy`) with the txHash and amount, using its existing key
3. Credits increment; key, history, and tier preserved

### Check credit balance
```bash
curl -s https://api.insumermodel.com/v1/credits \
  -H "X-API-Key: $INSUMER_API_KEY"
```

## Error handling

| Status | Endpoint | Cause | Fix |
|---|---|---|---|
| `400` | any | Missing required fields | Check request body |
| `401` | any auth'd | `X-API-Key` missing or invalid (on the three endpoints in the next row, a request with no key at all gets a `402` instead) | Verify env var, check spelling |
| `402` | `/v1/attest`, `/v1/trust`, `/v1/trust/batch` | With a key: out of credits. With no key at all: a pay-per-call quote, not a credit problem | With a key, Path 4 top-up (with approval) or Path 2 (human). With no key, set `INSUMER_API_KEY` and call again |
| `403` | `/v1/credits/buy` | Payment sender is not the wallet registered to this key | Send from the registered wallet, or add `"updateWallet": true` |
| `409` | `/v1/keys/create` | Free key already exists for this email | Reuse existing key |
| `409` | `/v1/keys/buy` | Wallet already has a key, or txHash already used | Wallet already has a key: top up via Path 4 instead (the same transaction can be used). txHash already used: that payment is spent, a new payment is needed |
| `422` | `/v1/keys/buy`, `/v1/credits/buy` | On-chain verification failed | Wait for confirmations, verify chain & amount |
| `429` | `/v1/keys/create` | 3 keys per IP per 24h, or free-key creation paused for the day | Wait 24h |
| `429` | any keyed endpoint | Daily request limit (100/day on free) | Wait for reset (`Retry-After`), or upgrade tier |

## Key hygiene (never violate)

- **Backend only.** `insr_live_...` is a long-lived backend credential. Never inline in source. Never expose in browser JS, `NEXT_PUBLIC_*`, `VITE_*`, `REACT_APP_*`, localStorage, or logs.
- **Env var pattern.** Always read from `process.env.INSUMER_API_KEY` / `os.environ["INSUMER_API_KEY"]`. Never hardcode in source files.
- **Don't echo the key in error messages.** Log "INSUMER_API_KEY not set" or "auth failed", not the key value or its suffix.
- **Don't commit `.env` files** containing the key. Use `.env.example` for the variable name only.

## Helper script

`scripts/create_key.py`: Python helper for Path 1. Reads `--email`, POSTs to `/v1/keys/create` with `appName: "insumer-agent-skills"` (override with `--app-name`), prints the key and a `.env` snippet.

```bash
python scripts/create_key.py --email you@example.com
```

For Path 3 (`/v1/keys/buy`) and Path 4 (`/v1/credits/buy`), the payment itself is made with the user's own wallet tooling, after their approval; these skills never sign or send a transaction. To submit the resulting transaction hash, the `curl` shapes above are sufficient, or use `scripts/buy_key.py` and `scripts/buy_credits.py`.

## Related skills

| Skill | Purpose |
|---|---|
| `insumer-attest` | Single-call wallet condition attestation |
| `insumer-trust` | Multi-dimensional wallet trust profile |
| `insumer-trust-batch` | Batch trust profiles for multiple wallets |
| `insumer-jwks-verify` | Offline ES256 verification of returned JWTs |

## References

- [Pricing & supported payment chains](https://insumermodel.com/pricing/)
- [Developer account portal (Stripe checkout)](https://insumermodel.com/developers/account/)
- [OpenAPI spec](https://insumermodel.com/openapi.yaml)
- [Public JWKS](https://insumermodel.com/.well-known/jwks.json)
