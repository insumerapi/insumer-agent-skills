---
name: insumer-auth
description: >
  InsumerAPI wallet auth: get an InsumerAPI key, configure INSUMER_API_KEY,
  check or top up InsumerAPI credits, or debug InsumerAPI 401/402/429 errors.
  Covers four key paths: free (email), paid (Stripe), an agent's first key
  paid on-chain, and an on-chain top-up of an existing key. The on-chain paths
  need the user's explicit approval of every payment.
metadata:
  version: "0.2.3"
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
- **Purchases are paid in USDC only.** Payments on Bitcoin or Tron, and USDT or any other token, are refused with a `400`
- **Platform wallet, USDC on Ethereum, Base, Polygon, Arbitrum, Optimism or Avalanche**: `0xee432065474D2C852700f74e3fD81e2Bcc16a3D4`
- **Platform wallet, USDC on BNB Chain**: `0xAd982CB19aCCa2923Df8F687C0614a7700255a23`. This previous address also still takes USDC on the other EVM chains during the changeover; it takes no USDT
- **Platform wallet, USDC on Solana**: `8fyEGM5tRjMocKQWaVXyM2XvvnTxR3sWdrYtug2zeLX4`. The previous Solana address `6a1mLjefhvSJX1sEX8PTnionbE9DqoYjU6F6bNkT4Ydr` still takes USDC during the changeover; it takes no USDT
- **Volume discounts** (paths 3 and 4): $5–$99 → 25 credits per $1 ($0.04/credit), $100–$499 → 33 credits per $1 (about $0.03/credit), $500+ → 50 credits per $1 ($0.02/credit). The price is per credit, not per call: an attestation costs 1 credit and a trust profile 3 (2 and 6 with `proof: "merkle"`)
- **Supported payment chains (these eight and no others)**: USDC on Ethereum (1), Base (8453), Polygon (137), Arbitrum (42161), Optimism (10), BNB Chain (56), Avalanche (43114) or Solana (`"solana"`). The other chains the API can read, Bitcoin and Tron included, are NOT payment chains, and funds sent on a chain outside this list cannot be recovered
- **Sender signature** (Path 3 always; Path 4 when the payment registers a wallet to the key): the wallet that sent the payment signs a fixed five-line text naming the payment, and the signature goes in `senderSignature`. See [Sign the sender text](#sign-the-sender-text)

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

For an agent whose operator has chosen to fund it. After the user approves the payment, USDC goes to the platform wallet, then the agent calls `POST /v1/keys/buy` with the transaction hash and the paying wallet's signature. **No email or prior authentication needed**: the sender wallet address from the transaction becomes the key's identity, and that wallet signs a short text to confirm it sent the payment.

### Step 1: Send payment

Send the desired amount (minimum $5) of USDC to the platform wallet for that chain, on one of the eight supported payment chains listed above. The address is the literal `recipient`.

### Step 2: Sign the sender text

The wallet that sent the payment signs the text in [Sign the sender text](#sign-the-sender-text), with `Purpose: key purchase`. To get the exact text, call Step 3 without `senderSignature`: the `400` carries it, and the payment is not used.

### Step 3: Call `/v1/keys/buy` with the transaction hash and the signature

```bash
curl -s -X POST https://api.insumermodel.com/v1/keys/buy \
  -H "Content-Type: application/json" \
  -d '{
    "txHash": "0xabc...",
    "chainId": 8453,
    "amount": 10,
    "senderSignature": "0x...",
    "appName": "insumer-agent-skills",
    "keyDelivery": "apiKey"
  }'
```

Default `appName` to `"insumer-agent-skills"` as in Path 1, unless the user names their app.

Fields:
- `txHash`: the transaction proving payment
- `chainId`: the chain the payment was sent on: the numeric chain ID for EVM, or `"solana"`
- `appName`: required. Name for the new key (the skills send `"insumer-agent-skills"`)
- `amount`: required. USDC amount sent (minimum 5)
- `senderSignature`: required. The paying wallet's signature over the sender text (see [Sign the sender text](#sign-the-sender-text))
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

The agent stores `data.key` in its secret store; that's its persistent identity going forward. One key per sender wallet address (returns `409` if the wallet already has a key).

**Important:** crypto sent on unsupported chains or to the wrong address cannot be recovered. All purchases are final.

---

## Path 4: Top up existing key (crypto, agent or human)

When an existing key (free, paid, or agent-onboarded) runs low on credits, top it up with a payment the user has approved to the platform wallet, then call `POST /v1/credits/buy`. **The key keeps its history, tier, and integrations**: credits just increment.

### Step 1: Send payment to the platform wallet

Same wallets and chains as Path 3: USDC only.

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
- `chainId`: the chain the payment was sent on: the numeric chain ID for EVM, or `"solana"`
- `amount`: USDC amount sent (minimum 5)

Sometimes required:
- `senderSignature`: the paying wallet's signature over the sender text, with `Purpose: credit purchase` (see [Sign the sender text](#sign-the-sender-text)). Required when the key has no registered wallet yet, and with `"updateWallet": true` from a different wallet. A top-up from the wallet already registered needs none.

Sender verification: the **first** top-up registers the sender wallet to the key, and that wallet signs the sender text. Subsequent top-ups must come from the **same** sender. To replace the registered wallet, send from the new wallet and include `"updateWallet": true` and a `senderSignature` from the new wallet.

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

## Sign the sender text

A transaction hash is public, so the API asks the wallet that sent the payment to sign a fixed text naming it. The API builds the text and checks the signature against the sender it read from the chain, never against an address the caller states. The text is five lines joined by `\n`, with no trailing newline:

```
api.insumermodel.com
Confirm the wallet that sent this payment.
Purpose: key purchase
Chain: eip155:8453
Transaction: 0xabc...
```

- `Purpose`: `key purchase` for `/v1/keys/buy`, `credit purchase` for `/v1/credits/buy`
- `Chain`: `eip155:<chainId>` for an EVM chain (for example `eip155:8453` for Base), or `solana`
- `Transaction`: the transaction id. EVM: `0x` plus the hash in lowercase hex. Solana: the signature as given

The simplest way to get the text exactly right: send the request without `senderSignature`. The API answers `400` with the exact text after a blank line, and the payment is not used. `scripts/buy_key.py` and `scripts/buy_credits.py` print it for you.

How to sign:
- **EVM**: EIP-191 `personal_sign` over the text (the wallet's "sign message"). Send the `0x` hex signature. Smart-contract wallets are accepted (ERC-1271)
- **Solana**: the wallet's `signMessage` over the UTF-8 text. Send the signature in base58 or base64

The user signs with their own wallet tooling; these skills never sign. Signing moves no funds, but it is the user's wallet: show the user the exact text before it is signed.

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
1. The operator approves the payment: amount, token, chain and recipient (for example $10 USDC on Base to `0xee432065474D2C852700f74e3fD81e2Bcc16a3D4`)
2. The payment is sent, and the paying wallet signs the sender text (`Purpose: key purchase`)
3. The agent calls Path 3 (`POST /v1/keys/buy`) with the txHash, `amount`, `senderSignature` and `"keyDelivery": "apiKey"`
4. Agent stores the returned `key` to its persistent secret store

### Agent runs out of credits mid-task
1. The operator approves a top-up, sent **from the same sender wallet that bought the original key**
2. Agent calls Path 4 (`POST /v1/credits/buy`) with the txHash and amount, using its existing key (no `senderSignature` needed from the registered wallet)
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
| `400` | `/v1/keys/buy`, `/v1/credits/buy` | Not paid in USDC on an accepted chain: Bitcoin, Tron, USDT, another token, or another `chainId` | Purchases are USDC only, on the eight payment chains above |
| `400` | `/v1/keys/buy`, `/v1/credits/buy` | `senderSignature` missing or not a string. The message carries the exact text to sign | Have the paying wallet sign that text, then send the same request with `senderSignature`. The payment has not been used |
| `401` | any auth'd | `X-API-Key` missing or invalid (on the three endpoints in the next row, a request with no key at all gets a `402` instead) | Verify env var, check spelling |
| `402` | `/v1/attest`, `/v1/trust`, `/v1/trust/batch` | With a key: out of credits. With no key at all: a pay-per-call quote, not a credit problem | With a key, Path 4 top-up (with approval) or Path 2 (human). With no key, set `INSUMER_API_KEY` and call again |
| `403` | `/v1/keys/buy`, `/v1/credits/buy` | `senderSignature` does not match the wallet that sent the payment. The message repeats the text to sign | Sign that exact text with the wallet that sent the payment, and retry |
| `403` | `/v1/credits/buy` | Payment sender is not the wallet registered to this key | Send from the registered wallet, or add `"updateWallet": true` and a `senderSignature` from the new wallet |
| `409` | `/v1/keys/create` | Free key already exists for this email | Reuse existing key |
| `409` | `/v1/keys/buy` | Wallet already has a key, or txHash already used | Wallet already has a key: top up via Path 4 instead (the same transaction can be used). txHash already used: that payment is spent, a new payment is needed |
| `422` | `/v1/keys/buy`, `/v1/credits/buy` | On-chain verification failed | Wait for confirmations, verify chain & amount |
| `422` | `/v1/keys/buy`, `/v1/credits/buy` | The wallet that sent the payment could not be determined, so the payment cannot be bound to a key | Send the next payment as a plain USDC transfer from one wallet. This payment cannot be used for a key or credits. |
| `429` | `/v1/keys/create` | 3 keys per IP per 24h, or free-key creation paused for the day | Wait 24h |
| `503` | `/v1/keys/buy`, `/v1/credits/buy` | The chain read, or a smart-wallet (ERC-1271) signature check, could not be completed. The payment has not been used | Retry the same request in a few seconds |
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

For Path 3 (`/v1/keys/buy`) and Path 4 (`/v1/credits/buy`), the payment itself is made with the user's own wallet tooling, after their approval; these skills never sign or send a transaction, and never sign the sender text. To submit the resulting transaction hash, the `curl` shapes above are sufficient, or use `scripts/buy_key.py` and `scripts/buy_credits.py`. Run either one without `--sender-signature` when a signature is needed: it prints the exact text to sign and how to sign it, and the payment is not used. Then run the same command again with `--sender-signature <signature>`.

```bash
python scripts/buy_key.py --tx 0xabc... --chain 8453 --amount 10
python scripts/buy_key.py --tx 0xabc... --chain 8453 --amount 10 --sender-signature 0x...
```

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
