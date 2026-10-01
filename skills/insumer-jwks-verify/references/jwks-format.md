# JWKS Format & Verification Reference

## JWKS document shape

`GET https://insumermodel.com/.well-known/jwks.json` returns a standard [RFC 7517](https://datatracker.ietf.org/doc/html/rfc7517) JWKS document:

```json
{
  "keys": [
    {
      "kty": "EC",
      "crv": "P-256",
      "x": "<base64url x coordinate>",
      "y": "<base64url y coordinate>",
      "use": "sig",
      "alg": "ES256",
      "kid": "insumer-attest-v1"
    },
    {
      "kty": "EC",
      "crv": "P-256",
      "x": "<base64url x coordinate>",
      "y": "<base64url y coordinate>",
      "use": "sig",
      "alg": "ES256",
      "kid": "insumer-attest-v2"
    },
    {
      "kty": "EC",
      "crv": "P-256",
      "x": "<base64url x coordinate>",
      "y": "<base64url y coordinate>",
      "use": "sig",
      "alg": "ES256",
      "kid": "insumer-trust-v2"
    },
    {
      "kty": "AKP",
      "alg": "ML-DSA-65",
      "use": "sig",
      "kid": "insumer-attest-pq1",
      "pub": "<base64url ML-DSA-65 public key>"
    },
    {
      "kty": "AKP",
      "alg": "ML-DSA-65",
      "use": "sig",
      "kid": "insumer-trust-pq1",
      "pub": "<base64url ML-DSA-65 public key>"
    }
  ]
}
```

Five entries over two keys: the three `EC` entries share one P-256 key and are selected by the response `kid`; the two `AKP` entries (RFC 9964) share one ML-DSA-65 key and are selected by the response `pqKid`. They are appended after the EC entries. Match on the kid you hold, never on position.

| Field | Value | Meaning |
|---|---|---|
| `kty` | `"EC"` or `"AKP"` | Elliptic-curve key (classical) or Algorithm Key Pair (post-quantum, RFC 9964) |
| `crv` | `"P-256"` | NIST P-256 curve (secp256r1) |
| `x`, `y` | base64url | Public key coordinates |
| `use` | `"sig"` | For signature verification |
| `alg` | `"ES256"` or `"ML-DSA-65"` | ECDSA with SHA-256 on the EC entries; FIPS 204 ML-DSA-65 on the AKP entries |
| `pub` | base64url | ML-DSA-65 public key (AKP entries only) |
| `kid` | `"insumer-attest-v1"`, `"insumer-attest-v2"`, `"insumer-trust-v2"` (EC); `"insumer-attest-pq1"`, `"insumer-trust-pq1"` (AKP) | Key identifier. The three EC kids resolve to the same key; the two AKP kids resolve to the same post-quantum key. Match the `kid` (or `pqKid`) on the response you are verifying, and fail closed if it does not resolve. |

The JWKS never requires authentication. Caching differs by URL; as observed on 2026-09-21, `https://insumermodel.com/.well-known/jwks.json` answered `Cache-Control: public, max-age=0, must-revalidate`, the `api.insumermodel.com/.well-known/jwks.json` mirror `max-age=14400` (4 hours), and `GET https://api.insumermodel.com/v1/jwks` `max-age=86400` (24 hours). Read the headers you actually receive rather than assuming a TTL, and treat an unknown kid as a reason to refetch, then fail closed.

## What's signed

For `/v1/attest` (raw form), the signed preimage is selected by `data.kid`:
- `insumer-attest-v2`: `"insumer.attestation.v2" + "\n" + canonical_json({ v: 2, id, pass, results, attestedAt })`, keys sorted recursively.
- `insumer-attest-v1`: the bare `JSON.stringify({ id, pass, results, attestedAt })` in that insertion order.
- Signed through `results`: every `evaluatedCondition`, `conditionHash`, `met`, and each result's chain anchor (`blockNumber`/`blockTimestamp`, or `slot`, `ledgerIndex`, `blockHeight`, `checkpointSequence`).
- NOT signed: `expiresAt` (bound to the signed `attestedAt` by spec Check 4), `passCount`/`failCount`, and the wallet itself. For most condition types the raw form does not name the wallet at all. In JWT form the wallet is the signed `sub` claim.
- Beside `sig`/`kid`, every response also carries `pqSig`/`pqKid` (ML-DSA-65 over the post-quantum domain tag plus the same classical preimage); in JWT form a sibling `pqJwt`.

For `/v1/trust` and `/v1/trust/batch`, selected by `kid`:
- `insumer-trust-v2`: `"insumer.trust.v2" + "\n" + canonical_json(trust)` where `trust` is the whole returned object (`id`, `wallet`, `conditionSetVersion`, `dimensions`, `summary`, `profiledAt`, `expiresAt`), no `v` member.
- `insumer-attest-v1`: the bare `JSON.stringify(trust)` in that order.
- `expiresAt` IS inside the trust preimage, unlike attestations.

## JWT claim mapping

`format: "jwt"` is available on `POST /v1/attest` only; `/v1/trust` and `/v1/trust/batch` return the raw `sig` form alone. When it is requested, the response includes a `data.jwt` field (and a sibling `data.pqJwt`, the post-quantum companion over the same claim set) with these claims:

| Claim | Source | Meaning |
|---|---|---|
| `iss` | `https://api.insumermodel.com` | Issuer |
| `sub` | wallet address | Subject: the wallet a condition in the request evaluated (with conditions across chain families, the first in the order EVM, Solana, XRPL, Bitcoin, Tron, Stellar, Sui) |
| `jti` | unique attestation ID | JWT ID — useful for replay defense |
| `iat` | unix timestamp | Issued at |
| `exp` | iat + 30 min, or iat + 5 min when the request carries an `erc7710_delegation` condition | Expiration, equal to the attestation's `expiresAt` |
| `pass` | boolean | Overall verification result |
| `results` | array | The attestation's `results`, unchanged: per-condition `met`, `evaluatedCondition`, `conditionHash`, and chain anchor |
| `conditionHash` | array of hex strings | SHA-256 of each condition's canonical evaluatedCondition. Top-level JWT payload aggregates one entry per condition (1-element array for single-condition requests). The per-result `conditionHash` inside `results[].conditionHash` is a single string. |
| `blockNumber` | hex string | The first result's EVM block number; absent when the first result carries none (non-EVM chains anchor in `results[i]` with `slot`, `ledgerIndex`, `blockHeight` or `checkpointSequence`) |
| `blockTimestamp` | ISO 8601 | The first result's block timestamp, when it has one |

## conditionHash recomputation

Each result's `conditionHash` is `0x` + SHA-256 of its `evaluatedCondition`, serialized per the scheme the `kid` selects. Verifiers can recompute it from `data.attestation.results[i].evaluatedCondition` (in JWT form, `results[i].evaluatedCondition`, compared with `results[i].conditionHash` and `conditionHash[i]`) to confirm exactly what condition logic was evaluated:

- `insumer-attest-v2` / `insumer-trust-v2`: canonical JSON, keys sorted recursively at every level, no whitespace. The function below.
- `insumer-attest-v1`: `JSON.stringify(evaluatedCondition, Object.keys(evaluatedCondition).sort())`, the top-level keys sorted and used as the replacer list. Byte-identical to the canonical form for a flat condition.

```python
import json
import hashlib

def recompute_condition_hash(evaluated_condition: dict) -> str:
    canonical = json.dumps(
        evaluated_condition,
        separators=(",", ":"),  # no whitespace
        sort_keys=True,
        ensure_ascii=False,     # match JavaScript's JSON.stringify
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return "0x" + digest
```

This is belt-and-suspenders — the JWT signature already covers `conditionHash` — but it lets a downstream service confirm the exact predicate, not just that *some* result was signed.

## Key rotation

Key changes are additive and signalled by the `kid` on each response. To date no kid has been removed from the JWKS: the v2 scheme (2026-06) added kids beside `insumer-attest-v1`, and the post-quantum companion (2026-09) added the two `AKP` entries beside the EC ones. Old kids keep verifying the artifacts they signed. A kid that does not resolve is unverifiable, not refuted.

Verifiers should:
- Always look up the public key by `kid` (don't hardcode)
- Use `createRemoteJWKSet` (jose) or `PyJWKClient` (PyJWT) for automatic refresh
- Never cache the public key directly — cache the JWKS document and let the library handle key lookup

## Failure modes

| Symptom | Likely cause | Action |
|---|---|---|
| `unknown kid` after rotation | Stale JWKS cache | Force refresh; if persistent, kid was retired |
| `JWT signature invalid` | Payload tampered or wrong key | Reject; do not retry with different keys |
| `JWT expired` (`exp` in past) | Past its `exp` (30 min, or 5 with a delegation condition) | Re-request a fresh attestation |
| `JWT issuer mismatch` | Response not from InsumerAPI | Reject |
| `algorithm not allowed` | Verifier didn't pin ES256 | Always pass `algorithms: ['ES256']` |

## Library-specific gotchas

### `jose` (Node)
- `createRemoteJWKSet` caches with `cooldownDuration` and `cacheMaxAge` — defaults are sane, don't override unless you know why
- Always pass `algorithms: ['ES256']` to `jwtVerify` — never accept `none` or default

### `PyJWT` (Python)
- Requires `pip install 'pyjwt[crypto]'` (the `cryptography` extra) for ES256 support
- `PyJWKClient.get_signing_key_from_jwt()` handles kid lookup automatically
- Pass `algorithms=["ES256"]` and `issuer="https://api.insumermodel.com"` to `jwt.decode()`

### `go-jose` (Go)
- Use `jose.ParseSigned` then verify against the JWKS keys
- Pin `Algorithm: jose.ES256`

## See also

- [SKILL.md](../SKILL.md) — usage examples and code emission rules
- [JWT spec (RFC 7519)](https://datatracker.ietf.org/doc/html/rfc7519)
- [JWS spec (RFC 7515)](https://datatracker.ietf.org/doc/html/rfc7515)
- [JWK spec (RFC 7517)](https://datatracker.ietf.org/doc/html/rfc7517)
- [`insumer-verify` on npm](https://www.npmjs.com/package/insumer-verify)
- [`insumer-verify` on PyPI](https://pypi.org/project/insumer-verify/) (Python; same checks, same test vectors)
