---
name: insumer-discount
description: >
  Token-holder discounts at InsumerAPI merchants: read a store's terms, check
  what a wallet qualifies for (free), optionally prove control of the wallet
  by signing an EIP-4361 message, and create a signed single-use discount code
  (INSR-XXXXX). Use when the user or agent wants a holder discount at a store
  in the InsumerAPI merchant directory, wants to know whether signing with the
  wallet gets a bigger discount, or needs a discount in ACP or UCP checkout
  format.
metadata:
  version: "0.1.0"
  author: InsumerAPI
---

# InsumerAPI Token-Holder Discounts

A store lists the tokens and NFTs it recognizes and the discount each earns. InsumerAPI reads the wallet, works out the discount, and issues a signed, single-use code (`INSR-XXXXX`, valid 30 minutes) that the store redeems. The store sees the code and the percentage, never the wallet or its balances.

**Two routes, the store sets the terms.**

- **Proven wallet:** the caller sends `walletProof`, a message signed by the wallet. The wallet gets the store's full discount, with no daily limit.
- **Unproven wallet:** no proof. The store decides what that gets: the same discount (the default), up to a lower percentage, or nothing, and optionally a daily limit per wallet.

Read the terms first, then decide whether signing is worth it.

## Setup

Get the API key from the `insumer-auth` skill, then:

```bash
export INSUMER_API_KEY='insr_live_...'
```

Creating a code uses one of the **merchant's** credits, not the caller's.

## Reference values (do not hallucinate)

- **API base**: `https://api.insumermodel.com`
- **Store terms**: `GET /v1/merchants/{merchantId}` → `data.walletTerms` (no key needed)
- **Free check**: `GET /v1/discount/check?merchant={merchantId}&wallet={0x...}` (no key needed)
- **Create a code**: `POST /v1/verify` with `X-API-Key` (also `POST /v1/acp/discount` and `POST /v1/ucp/discount` for checkout formats)
- **Validate a code**: `GET /v1/codes/{code}` (no key needed)
- **Proof message domain**: `api.insumermodel.com`
- **Proof message URI**: `https://api.insumermodel.com/v1/merchants/{merchantId}` (exactly this merchant)
- **Proof freshness**: signed within the last 5 minutes; every nonce used once
- **Proof wallets**: EVM wallets that sign with `personal_sign` (EIP-191). Smart-contract wallets are not accepted yet. Solana, XRPL and other wallets can still get the unproven terms.

## Usage

### Step 1: read the store's terms (free)

```bash
curl -s https://api.insumermodel.com/v1/merchants/acme-store
```

```json
"walletTerms": {
  "proofAccepted": ["evm"],
  "proven":   { "maxDiscountsPerWalletPerDay": null },
  "unproven": { "maxDiscount": 5, "maxDiscountsPerWalletPerDay": 10 }
}
```

`unproven.maxDiscount`: `null` = the same as proven, `0` = no discount without proof, otherwise at most that percent. `unproven.maxDiscountsPerWalletPerDay`: `null` = no limit.

### Step 2: check what the wallet qualifies for (free)

```bash
curl -s "https://api.insumermodel.com/v1/discount/check?merchant=acme-store&wallet=0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
```

`totalDiscount` is what the wallet gets **without** proof. If `discountIfProven` is present, signing gets that instead. If it is absent, signing changes the discount by nothing (it still lifts the daily limit).

### Step 3 (optional): prove the wallet

Sign this exact message with the wallet, using `personal_sign`:

```
api.insumermodel.com wants you to sign in with your Ethereum account:
0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

Prove wallet for a discount.

URI: https://api.insumermodel.com/v1/merchants/acme-store
Version: 1
Chain ID: 1
Nonce: k3j9x2m8q1
Issued At: 2026-10-05T18:00:00.000Z
```

Line 2 is the wallet (checksummed or lowercase), the URI names the merchant, the nonce is fresh random letters and digits (8 or more), and `Issued At` is the current time in ISO 8601. `scripts/proof_message.py` builds it for you.

### Step 4: create the code

```bash
curl -X POST https://api.insumermodel.com/v1/verify \
  -H "X-API-Key: $INSUMER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "merchantId": "acme-store",
    "wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "walletProof": { "message": "<the message, exactly as signed>", "signature": "0x..." }
  }'
```

Leave out `walletProof` for the unproven route. The response carries `code`, `totalDiscount`, `walletProven`, and `discountIfProven` when proof would have got more. `GET /v1/codes/{code}` reports the code's percentage, expiry and `walletProven`.

## Code emission rules

When emitting integration code for this flow, the agent MUST:

1. **Read the terms or run the free check before creating a code.** Creating a code spends a merchant credit even when the wallet qualifies for nothing.
2. **Never hold the user's private key to sign for them.** The wallet's owner signs, in their own wallet. An agent signs only with a wallet it controls itself.
3. **Build a fresh message for every request.** A nonce is accepted once, and a message older than 5 minutes is refused.
4. **Send the proof with `wallet` only.** A proof sent with `solanaWallet` or `xrplWallet` is a `400`.
5. **Treat a failed proof as a failed proof.** A `401` on a request with `walletProof` means the proof was refused (wrong wallet, merchant, domain, expired, nonce reused or bad signature); no credit was used. Fix and re-sign, or retry without proof to take the unproven terms. It never silently falls back.
6. **Read the API key from an env var**, and call from a backend.

## Helper scripts

`scripts/proof_message.py`: prints the EIP-4361 message for a wallet and merchant, with a fresh nonce and the current time. It never signs and never handles a private key: the wallet signs the printed message itself, and you save `{ "message": ..., "signature": ... }` as the proof file.

```bash
python scripts/proof_message.py --merchant acme-store --wallet 0xd8dA...6045
```

`scripts/discount.py`: reads the terms, runs the free check, and with `--create` creates the code (adding `--proof-file proof.json` for the proven route).

```bash
python scripts/discount.py --merchant acme-store --wallet 0xd8dA...6045
python scripts/discount.py --merchant acme-store --wallet 0xd8dA...6045 --create --proof-file proof.json
```

## Error handling

| Status | Cause | Fix |
|---|---|---|
| `400` | Missing or invalid field; proof sent with a non-EVM wallet | Check the request body |
| `401` | Missing API key, or a `walletProof` that was refused | See `insumer-auth`; re-sign a fresh message |
| `402` | The merchant has no credits left | Nothing the caller can do; tell the user |
| `403` | The merchant has not enabled app access | Nothing the caller can do |
| `429` | The key's daily limit, or the store's daily limit for an unproven wallet | Prove the wallet (no daily limit), or try tomorrow |
| `503` | A read did not complete (`rpc_failure`) | Retry after a short delay; no credit used |

A `503` with `rpc_failure` is never "not eligible". Retry the call.

## Related skills

| Skill | Purpose |
|---|---|
| `insumer-auth` | Get a free API key, configure env vars |
| `insumer-jwks-verify` | Verify signed responses offline |
| `insumer-attest` | Signed yes/no on any wallet condition |

## References

- [InsumerAPI OpenAPI spec](https://insumermodel.com/openapi.yaml)
- [EIP-4361: Sign-In with Ethereum](https://eips.ethereum.org/EIPS/eip-4361)
