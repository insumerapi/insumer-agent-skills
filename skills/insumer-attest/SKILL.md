---
name: insumer-attest
description: >
  Wallet auth via InsumerAPI: condition-based access with ES256-signed,
  JWKS-verifiable boolean responses (token balances across 37 chains, plus NFT
  ownership, EAS attestations, Farcaster IDs and other condition types). Use
  when the user wants InsumerAPI to give a "verified yes or no" on whether a
  wallet satisfies an on-chain condition, to gate a feature by what a wallet
  holds with InsumerAPI, or to compose an InsumerAPI wallet_state signal in a
  multi-issuer trust envelope. Read, evaluate, sign, in one call.
metadata:
  version: "0.2.0"
  author: InsumerAPI
---

# InsumerAPI Wallet Condition Attestation

**Boolean, not balance.** A signed `true`/`false` answering "does this wallet satisfy this condition right now?" — never the underlying balance. The response is ES256-signed and verifiable offline against the public JWKS at `https://insumermodel.com/.well-known/jwks.json`. The signing key never leaves the issuer; anyone holding the JWKS can independently re-run the verification.

You send conditions in. You get cryptographically verifiable results out.

## The primitive

Wallet auth is the OAuth-equivalent for what a wallet holds. The pattern is **read → evaluate → sign**:

1. **Read** — InsumerAPI reads the wallet's on-chain state on the requested chain
2. **Evaluate** — wallet state is checked against the supplied condition
3. **Sign** — a boolean result is returned, ES256-signed, with a `conditionHash` for tamper detection and a block anchor for replay defense

**No secrets. No identity-first. No static credentials.** Token gating is one form of condition-based access; this is the general primitive.

## Capabilities

- Single-call attestation across 37 chains: 31 EVM, Solana, XRPL, Bitcoin, Tron, Stellar, Sui
- Up to 10 conditions per request — overall `pass` is `true` only if every condition is `true`
- Nine condition types: `token_balance`, `nft_ownership` (33 of 37 chains: EVM + Solana + XRPL), `eas_attestation` (Ethereum, Optimism, Polygon, Base, Arbitrum), `farcaster_id`, `evm_view_call` (single-address-argument view function returning bool; `selector` required, EVM chains only), `ratio_to_amount`, `ratio_to_supply`, `erc8004_agent` (Base; `agentId` required), `erc7710_delegation` (Base; `delegationManager`, `expectedDelegator`, `delegation` required; max 3 per call, 5-minute expiry)
- ES256 signature on every response, with optional ES256 JWT (`format: "jwt"`) for standard JWT-library verification
- Optional EIP-1186 Merkle storage proofs (`proof: "merkle"`) on token_balance conditions for 27 of the 31 EVM chains (not ZKsync Era, Sei, Viction or XDC Network, nor any non-EVM chain), plus revocation-slot proofs for erc7710_delegation on the verified v1.3.0 manager
- 30-minute attestation TTL, 5 minutes when the request includes an `erc7710_delegation` condition (`expiresAt` in response)

## Setup

Get the API key from the `insumer-auth` skill, then:

```bash
export INSUMER_API_KEY='insr_live_...'
```

## Reference values (do not hallucinate)

- **API base**: `https://api.insumermodel.com`
- **JWKS URL**: `https://insumermodel.com/.well-known/jwks.json`
- **Signing algorithm**: ES256 (ECDSA P-256)
- **Key IDs (`kid`)**: three over the same P-256 key — `insumer-attest-v2` (attest, every key issued since 2026-06-10), `insumer-trust-v2` (trust), `insumer-attest-v1` (pre-cutover keys, and the commerce discount path). **Resolve the key by the `kid` on the response; never pin one and never take `keys[0]`.** The `kid` also selects the verification rules: v1 signs bare JSON, v2 signs a domain-separated canonical preimage.
- **Auth header**: `X-API-Key: insr_live_...`
- **Attestation TTL**: 30 minutes, or 5 when the request includes an `erc7710_delegation` condition (`expiresAt` in response)
- **Signature format**: base64 P1363 (88 chars) on the `sig` field; ES256 JWT on the `jwt` field when `format: "jwt"` is requested

## Usage

### Example 1: ERC-20 balance threshold

User says: "Check if `0xd8dA...6045` holds at least 100 USDC on Base."

```bash
curl -X POST https://api.insumermodel.com/v1/attest \
  -H "X-API-Key: $INSUMER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "conditions": [
      {
        "type": "token_balance",
        "contractAddress": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "chainId": 8453,
        "threshold": "100",
        "label": "USDC >= 100 on Base"
      }
    ]
  }'
```

Returns `{ "ok": true, "data": { "attestation": { "pass": true|false, ... }, "sig": "...", "kid": "insumer-attest-v2" }, "meta": { "creditsRemaining": ..., "creditsCharged": 1, ... } }`.

### Example 2: NFT ownership

```bash
curl -X POST https://api.insumermodel.com/v1/attest \
  -H "X-API-Key: $INSUMER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "conditions": [
      {
        "type": "nft_ownership",
        "contractAddress": "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D",
        "chainId": 1,
        "label": "Bored Ape holder"
      }
    ]
  }'
```

### Example 3: EAS attestation via compliance template

```bash
curl -X POST https://api.insumermodel.com/v1/attest \
  -H "X-API-Key: $INSUMER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "conditions": [
      {
        "type": "eas_attestation",
        "template": "coinbase_verified_account",
        "label": "Coinbase KYC verified"
      }
    ]
  }'
```

Available templates: see `references/condition-shapes.md` or `GET https://api.insumermodel.com/v1/compliance/templates`.

### Example 4: JWT format for standard library verification

Add `"format": "jwt"` to the request body to receive an ES256 JWT in the response (no extra cost). Verify with `jose` (Node), `PyJWT` (Python), `go-jose` (Go), etc., pointed at the JWKS URL. See the `insumer-jwks-verify` skill for the canonical recipe.

### Example 5: Merkle storage proofs (advanced)

```bash
curl -X POST https://api.insumermodel.com/v1/attest \
  -H "X-API-Key: $INSUMER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "proof": "merkle",
    "conditions": [
      {
        "type": "token_balance",
        "contractAddress": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "chainId": 8453,
        "threshold": "100",
        "label": "USDC >= 100 on Base"
      }
    ]
  }'
```

`proof: "merkle"` returns EIP-1186 storage proofs alongside the boolean and **costs 2 credits instead of 1** (1 if no proof could be delivered). **Note**: Merkle mode reveals the raw on-chain balance to the caller — standard mode does not. Only opt in if the consumer needs the raw balance.

### Example 6: XRPL trust line

```bash
curl -X POST https://api.insumermodel.com/v1/attest \
  -H "X-API-Key: $INSUMER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "xrplWallet": "rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH",
    "conditions": [
      {
        "type": "token_balance",
        "contractAddress": "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De",
        "chainId": "xrpl",
        "currency": "RLUSD",
        "threshold": "50",
        "label": "RLUSD >= 50 on XRPL"
      }
    ]
  }'
```

XRPL conditions use `xrplWallet` instead of `wallet` and require a `currency` field. See `references/chains.md` for the full chain coverage table.

## Code emission rules

When emitting integration code that calls `/v1/attest`, the agent MUST:

1. **Read the API key from an env var.** Never inline `insr_live_...`.
2. **Verify the signature offline.** Pair this skill with `insumer-jwks-verify`. The signed boolean is the product — the JSON body alone is untrusted.
3. **Do not send `decimals`.** It is optional. Leave it out: the token's own decimals are always read from the chain. If sent it is only a cross-check, and a value that differs from the token's own decimals is rejected with a `400`.
3a. **Send the `token_balance` `threshold` as a decimal string** (`"100"`, not `100`). Keys created from 2026-06-10 sign with `kid: insumer-attest-v2` and reject a JSON number with a `400`; a string is accepted by both v1 and v2 keys.
4. **Call from a backend, not a browser.** The API key is a backend credential.
5. **Don't cache the verdict.** Cache the JWKS (the `jose` library's `createRemoteJWKSet` does this for you). Pass/fail expires at `expiresAt` (30 minutes, or 5 for an `erc7710_delegation` condition), and wallet state changes.
6. **Don't request `proof: "merkle"` unless the caller needs the raw balance.** Standard mode is boolean-not-balance by construction; Merkle mode opts out of that privacy property.

## Helper script

`scripts/attest.py` — Python helper that wraps `POST /v1/attest`. Reads `INSUMER_API_KEY` from env, accepts the full JSON request body (wallet + conditions) on stdin or via `--body-file`, prints the signed response.

```bash
echo '{"wallet":"0x...","conditions":[{"type":"token_balance",...}]}' | python scripts/attest.py
```

## Error handling

| Status | Cause | Fix |
|---|---|---|
| `400` | Missing/invalid wallet, conditions, or condition fields | Check request body against `references/condition-shapes.md` |
| `401` | Missing or invalid API key | See `insumer-auth` skill |
| `402` | Out of verification credits | Top up via Path 4 in `insumer-auth`, only after the user approves the payment |
| `503` | Upstream blockchain data source unavailable | Retryable after a short delay; no credits charged |

A `503` carries error code `rpc_failure`. It means a read did not complete and nothing was signed. It is never a `false`: do not report it as a condition that was not met. Retry the call.

## Related skills

| Skill | Purpose |
|---|---|
| `insumer-auth` | Get a free API key, configure env vars |
| `insumer-jwks-verify` | Offline ES256 verification of the response |
| `insumer-trust` | Curated multi-dimensional wallet profile (alternative to custom conditions) |

## References

- [chains.md](references/chains.md): full 37-chain coverage table
- [condition-shapes.md](references/condition-shapes.md) — every supported condition type with full request shape
- [InsumerAPI OpenAPI spec](https://insumermodel.com/openapi.yaml)
- [Public JWKS](https://insumermodel.com/.well-known/jwks.json)
