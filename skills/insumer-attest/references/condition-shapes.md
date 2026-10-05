# Condition Shapes

Every condition object passed in `/v1/attest` (`conditions[]` array, 1–10 items) has a shape determined by its `type` field. The API accepts nine condition types. This file documents the four core shapes (`token_balance`, `nft_ownership`, `eas_attestation`, `farcaster_id`). The other five (`evm_view_call`, `ratio_to_amount`, `ratio_to_supply`, `erc8004_agent`, `erc7710_delegation`) are listed with their required fields under Capabilities in this skill's `SKILL.md` and specified in full in the [OpenAPI spec](https://insumermodel.com/openapi.yaml).

## 1. `token_balance`

Threshold check on a fungible token balance.

```json
{
  "type": "token_balance",
  "contractAddress": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  "chainId": 8453,
  "threshold": "100",
  "label": "USDC >= 100 on Base"
}
```

| Field | Required | Notes |
|---|---|---|
| `contractAddress` | yes | Token contract (0x + 40 hex on EVM), or `"native"` for the chain's native coin. `"native"` is for `token_balance` and `ratio_to_amount` only. For XRPL: `"native"` for XRP, or the issuer r-address for trust lines. For Bitcoin: must be `"native"`. For Sui: always a coin type (`address::module::Name`); native SUI is `"0x2::sui::SUI"` and `"native"` is a `400`. |
| `chainId` | yes | Numeric for EVM, `"solana"`/`"xrpl"`/`"bitcoin"`/`"tron"`/`"stellar"`/`"sui"` for non-EVM |
| `threshold` | yes | Minimum balance in **human units**, as a **decimal string** (`"100"`, `"0.000001"` — not a JSON number). Keys signing with `kid: insumer-attest-v2` (created from 2026-06-10) reject a number with a `400`; a string is accepted by v1 and v2 alike. Must be `> 0` (use `"0.000001"` for prove-any-balance). |
| `decimals` | optional | Cross-check only; leave it out. The token's own decimals are always read from the chain. If sent, a value that differs from the token's own decimals is rejected with a `400`. |
| `currency` | XRPL only | Trust line currency code (e.g. `"RLUSD"`, `"USDC"`). Case-sensitive: send it exactly as issued |
| `label` | recommended | Human-readable label (max 100 chars) |

Operator: `gte` (>=).

## 2. `nft_ownership`

Check whether the wallet owns at least one NFT in a collection.

```json
{
  "type": "nft_ownership",
  "contractAddress": "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D",
  "chainId": 1,
  "label": "Bored Ape holder"
}
```

| Field | Required | Notes |
|---|---|---|
| `contractAddress` | yes | NFT contract address (ERC-721 style on EVM, NFToken issuer on XRPL). 0x + 40 hex on EVM; `"native"` is a `400` here (use `token_balance` for the native coin). |
| `chainId` | yes | |
| `taxon` | XRPL only | Filter by issuer + taxon (optional, NFToken filtering on XRPL) |
| `label` | recommended | |

Operator: `gt` (> 0).

## 3. `eas_attestation`

Verify the wallet has a valid EAS (Ethereum Attestation Service) attestation.

### Via compliance template (preferred)

```json
{
  "type": "eas_attestation",
  "template": "coinbase_verified_account",
  "label": "Coinbase KYC verified"
}
```

Available templates (current list — fetch live from `GET https://api.insumermodel.com/v1/compliance/templates`):

| Template | Provider | Chain |
|---|---|---|
| `coinbase_verified_account` | Coinbase | Base (8453) |
| `coinbase_verified_country` | Coinbase | Base (8453) |
| `coinbase_one` | Coinbase | Base (8453) |
| `gitcoin_passport_score` | Gitcoin | Optimism (10) |
| `gitcoin_passport_active` | Gitcoin | Optimism (10) |

### Via raw schema ID (advanced)

```json
{
  "type": "eas_attestation",
  "schemaId": "0xf8b05c79f090979bf4a80270aba232dff11a10d9ca55c4f88de95317970f0de9",
  "attester": "0x357458739F90461b99789350868CD7CF330Dd7EE",
  "indexer": "0x2c7eE1E5f416dfF40054c27A62f7B357C4E8619C",
  "chainId": 8453,
  "label": "Coinbase Verified Account"
}
```

| Field | Required | Notes |
|---|---|---|
| `template` | one-of | Compliance template name |
| `schemaId` | one-of | Raw EAS schema ID (with `indexer` and `chainId`; `attester` optional) |
| `attester` | optional | Trusted attester address |
| `indexer` | with schemaId | EAS indexer contract address |
| `chainId` | with schemaId | EAS is read on Ethereum (1), Optimism (10), Polygon (137), Base (8453) and Arbitrum (42161) only |

Operator: `valid`.

## 4. `farcaster_id`

Check whether the wallet has a registered Farcaster ID.

```json
{
  "type": "farcaster_id",
  "label": "Has Farcaster account"
}
```

Operator: `registered`.

## Composing multiple conditions

Up to 10 conditions per request. Overall `pass` is `true` only if **every** condition passes. Each individual condition's result is also returned in `data.attestation.results[]`.

```json
{
  "wallet": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
  "conditions": [
    {
      "type": "token_balance",
      "contractAddress": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "chainId": 8453,
      "threshold": "100",
      "label": "USDC >= 100 on Base"
    },
    {
      "type": "eas_attestation",
      "template": "coinbase_verified_account",
      "label": "Coinbase KYC"
    }
  ]
}
```

This evaluates to `pass: true` only if the wallet holds 100+ USDC on Base AND has a Coinbase-verified attestation.

## Cross-chain wallets in one call

Pass multiple wallet fields to verify across ecosystems:

```json
{
  "wallet": "0xabc...",
  "solanaWallet": "5xY...",
  "xrplWallet": "rN7n...",
  "bitcoinWallet": "bc1q...",
  "conditions": [
    { "type": "token_balance", "chainId": 1, "contractAddress": "0x...", "threshold": "1000" },
    { "type": "token_balance", "chainId": "solana", "contractAddress": "EPjF...", "threshold": "100" },
    { "type": "token_balance", "chainId": "xrpl", "contractAddress": "rMxC...", "currency": "RLUSD", "threshold": "50" },
    { "type": "token_balance", "chainId": "bitcoin", "contractAddress": "native", "threshold": "0.01" }
  ]
}
```

The API routes each condition to the matching wallet field by `chainId`.
