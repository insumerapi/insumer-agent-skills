---
name: insumer-jwks-verify
description: >
  Offline ES256 verification of InsumerAPI signed responses against the public
  JWKS. Use when the user receives a signed attestation from /v1/attest,
  /v1/trust, or /v1/trust/batch and needs to verify the signature without
  trusting the JSON body. Covers both the JWT path (jose / PyJWT / go-jose) and
  the raw sig path (ES256 over the canonical attestation/trust object).
metadata:
  version: "0.2.0"
  author: InsumerAPI
---

# InsumerAPI Offline JWKS Verification

The signed boolean is the product. The JSON body alone is untrusted — anyone can fabricate a JSON response. **Verify the signature, every time.**

InsumerAPI signs every `/v1/attest`, `/v1/trust`, and `/v1/trust/batch` response with ES256 (ECDSA P-256). The public key is published as a standard JWKS at `https://insumermodel.com/.well-known/jwks.json`. The signing key never leaves the issuer; anyone holding the JWKS can independently re-run the verification — no callback to InsumerAPI required.

## Reference values (do not hallucinate)

- **JWKS URL**: `https://insumermodel.com/.well-known/jwks.json`
- **Algorithm**: ES256 (ECDSA P-256)
- **Key IDs (`kid`)**: five JWKS entries over two keys. Three EC kids on the same P-256 key: `insumer-attest-v2` (attest, every key issued since 2026-06-10), `insumer-trust-v2` (trust), `insumer-attest-v1` (pre-cutover keys, and the commerce discount path). Then two RFC 9964 `AKP` entries for the ML-DSA-65 post-quantum companion key: `insumer-attest-pq1` and `insumer-trust-pq1`, selected by the response `pqKid`. Resolve by kid, never by position; fail closed on an unknown kid.
- **JWT issuer claim** (when `format: "jwt"` is requested): `https://api.insumermodel.com`
- **Raw signature format**: base64 P1363 (88 chars) on the `sig` field

## Two verification paths

InsumerAPI returns up to **two** verifiable forms in a signed response:

1. **`sig` field** (every response): base64 P1363 ES256 signature over the preimage the `kid` selects (see "What's signed" in `references/jwks-format.md`). Attestations: for `insumer-attest-v2`, the domain tag `insumer.attestation.v2` + newline + canonical JSON (keys sorted recursively, no whitespace) of `{v:2, id, pass, results, attestedAt}`; for `insumer-attest-v1`, `JSON.stringify({id, pass, results, attestedAt})` in that insertion order. Trust profiles: for `insumer-trust-v2`, the domain tag `insumer.trust.v2` + newline + canonical JSON of the whole `trust` object; for `insumer-attest-v1`, `JSON.stringify(trust)` as issued. Verify with any ES256 library + the JWKS key the `kid` names. Every response also carries `pqSig`/`pqKid`, an ML-DSA-65 companion over the same preimage under a post-quantum domain tag (spec Check 6).
2. **`jwt` field** *(`/v1/attest` only, and only when `"format": "jwt"` is in the request body; `/v1/trust` and `/v1/trust/batch` have no JWT form)* — standard ES256 JWT carrying the attestation as claims, with a sibling `pqJwt` companion. Verify with any standard JWT library pointed at the JWKS URL.

The `jwt` path is easier when the consumer is already using a JWT library, and it signs the wallet as the `sub` claim. The raw `sig` path is more compact, but for most condition types it does not sign the wallet: it proves that some wallet met the condition, not which one. Use the JWT form (or an `erc8004_agent` / `erc7710_delegation` condition, which carry the wallet in the signed result) whenever the relying party must know which wallet was attested.

## Recipe 1: JWT verification (Node.js, `jose`)

Add `"format": "jwt"` to the `/v1/attest` request body (trust profiles have no JWT form; use Recipe 3), then:

```javascript
import { createRemoteJWKSet, jwtVerify } from 'jose';

const JWKS = createRemoteJWKSet(
  new URL('https://insumermodel.com/.well-known/jwks.json')
);

async function verifyAttestation(jwtString) {
  const { payload } = await jwtVerify(jwtString, JWKS, {
    issuer: 'https://api.insumermodel.com',
    algorithms: ['ES256'],
  });
  // payload.pass is the verified boolean
  // payload.conditionHash, payload.blockNumber, payload.blockTimestamp
  // are also verified as part of the signed JWT
  return payload;
}
```

`createRemoteJWKSet` caches the JWKS automatically with sane defaults. Don't fetch the JWKS yourself on every call.

## Recipe 2: JWT verification (Python, `PyJWT` + `cryptography`)

```python
import jwt
from jwt.jwks_client import PyJWKClient

jwks_client = PyJWKClient("https://insumermodel.com/.well-known/jwks.json")

def verify_attestation(jwt_string: str) -> dict:
    signing_key = jwks_client.get_signing_key_from_jwt(jwt_string)
    payload = jwt.decode(
        jwt_string,
        signing_key.key,
        algorithms=["ES256"],
        issuer="https://api.insumermodel.com",
    )
    # payload["pass"] is the verified boolean
    return payload
```

## Recipe 3: Raw `sig` verification (Node.js)

For any response's `sig` (every trust profile, and attestations without `format: "jwt"`). Pass `response.data` for `/v1/attest` and `/v1/trust`, or one entry of `data.results[]` for `/v1/trust/batch`, exactly as parsed from the wire; never rebuild or re-order the signed object, because the v1 scheme signs insertion-order `JSON.stringify` output.

```javascript
// Canonical JSON: keys sorted recursively at every level, no whitespace.
function canonicalize(value) {
  if (Array.isArray(value)) return '[' + value.map(canonicalize).join(',') + ']';
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort()
      .map((k) => JSON.stringify(k) + ':' + canonicalize(value[k])).join(',') + '}';
  }
  return JSON.stringify(value);
}

// The exact bytes the ES256 signature covers, selected by kid.
function signedPreimage(data) {
  const { kid } = data;
  if (data.attestation) {
    const { id, pass, results, attestedAt } = data.attestation;
    if (kid === 'insumer-attest-v2') {
      return 'insumer.attestation.v2\n' + canonicalize({ v: 2, id, pass, results, attestedAt });
    }
    if (kid === 'insumer-attest-v1') return JSON.stringify({ id, pass, results, attestedAt });
  } else if (data.trust) {
    if (kid === 'insumer-trust-v2') return 'insumer.trust.v2\n' + canonicalize(data.trust);
    if (kid === 'insumer-attest-v1') return JSON.stringify(data.trust);
  }
  throw new Error(`kid ${kid} does not sign this artifact`); // fail closed
}

async function verifyRawSig(data, jwks) {
  const jwk = jwks.keys.find((k) => k.kty === 'EC' && k.kid === data.kid);
  if (!jwk) throw new Error(`unknown kid ${data.kid}`); // fail closed
  const key = await crypto.subtle.importKey(
    'jwk', { kty: jwk.kty, crv: jwk.crv, x: jwk.x, y: jwk.y },
    { name: 'ECDSA', namedCurve: 'P-256' }, false, ['verify']);
  // Web Crypto takes the 64-byte P1363 (r || s) signature as is.
  return crypto.subtle.verify(
    { name: 'ECDSA', hash: 'SHA-256' }, key,
    Buffer.from(data.sig, 'base64'),
    new TextEncoder().encode(signedPreimage(data)));
}
```

This checks the ES256 signature only. It does not check condition hashes, expiry, or the post-quantum companion. For all of those, use the official package, **`insumer-verify`** on npm (ES module; import it, do not `require` it):

```bash
npm install insumer-verify @noble/post-quantum
```

`@noble/post-quantum` is an optional peer of `insumer-verify`. Without it, every response still verifies classically, but `checks.pq.status` reports `unverifiable` for a companion that is present, so the post-quantum signature is never actually checked.

In Python, the same package is on PyPI under the same name, runs the same checks and passes the same 27 published test vectors:

```bash
pip install "insumer-verify[pq]"
```

```python
from insumer_verify import verify_attestation, verify_trust_profile

opts = {"jwks_url": "https://insumermodel.com/.well-known/jwks.json"}
result = verify_attestation(response, **opts)        # the full /v1/attest response, or a JWT string
if result["valid"] and response["data"]["attestation"]["pass"]:
    ...
profile = verify_trust_profile(trust_response, **opts)  # render profile["trust"] only when profile["valid"]
```

Without `dilithium-py` (the `[pq]` extra) the companion is reported `unverifiable`, exactly as the npm package behaves without `@noble/post-quantum`.

```javascript
import { verifyAttestation, verifyTrustProfile } from 'insumer-verify';

const opts = { jwksUrl: 'https://insumermodel.com/.well-known/jwks.json' };

// /v1/attest: pass the full response ({ ok, data: { attestation, sig, kid, pqSig, pqKid, ... } }).
const result = await verifyAttestation(response, opts);
// result.valid is the AND of the checks; result.checks reports each one separately:
// checks.signature, checks.conditionHashes, checks.freshness, checks.expiry, and
// checks.pq (the post-quantum companion: status verified | refuted | absent | unverifiable).
// For a whole format:"jwt" response (data.jwt beside data.attestation) there is also
// checks.jwt, which verifies the tokens and binds them to the attestation.
if (!result.valid) throw new Error('attestation rejected: ' + JSON.stringify(result.checks));

// /v1/trust: pass the full response; for /v1/trust/batch, call once per data.results[i].
const trust = await verifyTrustProfile(trustResponse, opts);
// trust.checks: signature, freshness, expiry, pq. Render trust.trust (the verified object), gated on trust.valid.
if (!trust.valid) throw new Error('trust profile rejected: ' + JSON.stringify(trust.checks));
```

## Recipe 4: Conditional verification + tamper detection

Beyond signature verification, you can independently re-derive the `conditionHash` to confirm the condition wasn't tampered with:

```javascript
import { createHash } from 'node:crypto';

// conditionHash = "0x" + SHA-256 over evaluatedCondition, serialized per the kid:
// v2 kids: canonical JSON, keys sorted recursively at every level, no whitespace.
// insumer-attest-v1: JSON.stringify with the sorted top-level keys as the replacer.
function canonicalize(value) {
  if (Array.isArray(value)) return '[' + value.map(canonicalize).join(',') + ']';
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort()
      .map((k) => JSON.stringify(k) + ':' + canonicalize(value[k])).join(',') + '}';
  }
  return JSON.stringify(value);
}

function recomputeConditionHash(evaluatedCondition, kid) {
  const bytes = kid === 'insumer-attest-v1'
    ? JSON.stringify(evaluatedCondition, Object.keys(evaluatedCondition).sort())
    : canonicalize(evaluatedCondition);
  return '0x' + createHash('sha256').update(bytes).digest('hex');
}

// After signature verification (Recipe 1), re-derive and compare every condition.
// In the JWT payload, conditionHash is an array (one entry per condition) and each
// evaluatedCondition lives in results[i]. kid is the JWT header's kid
// (jwtVerify returns it as protectedHeader.kid).
payload.results.forEach((r, i) => {
  const recomputed = recomputeConditionHash(r.evaluatedCondition, kid);
  if (recomputed !== r.conditionHash || recomputed !== payload.conditionHash[i]) {
    throw new Error(`conditionHash mismatch on condition ${i}: payload may have been tampered with`);
  }
});
```

For the raw form, the same loop runs over `data.attestation.results` with `data.kid`.

## Code emission rules

1. **Cache the JWKS, not the verdict.** Libraries like `jose`'s `createRemoteJWKSet` and `PyJWT`'s `PyJWKClient` cache automatically with TTL. Do not cache `pass` — wallet state changes and the attestation has an `expiresAt` 30 minutes out (5 with a delegation condition).
2. **Pin the algorithm.** Always pass `algorithms: ['ES256']` — never accept any algorithm. This blocks "alg confusion" attacks.
3. **Pin the issuer.** Always pass `issuer: 'https://api.insumermodel.com'` for JWT verification.
4. **Verify in the trust boundary.** Verify on the server that's making the access decision — never verify in the browser and trust the result. (Browsers can verify; they just can't be the trust boundary.)
5. **Fail closed.** If verification throws, deny access. Never default to "allow" on verification failure.

## Helper script

`scripts/verify.py` — Python helper that takes a JWT, or a response object carrying `jwt` (from `/v1/attest` with `format: "jwt"`), on stdin and verifies the JWT against the public JWKS. Prints `OK` + payload, or `INVALID` + reason. It does not verify raw `sig` responses (every trust profile, and attestations without `format: "jwt"`), condition hashes, the expiry binding or the post-quantum companion. For every check in Python, `pip install insumer-verify` (above) is the complete path; use Recipe 3 or `insumer-verify` on npm in JavaScript.

```bash
echo '{"jwt":"eyJhbG...","kid":"insumer-attest-v2"}' | python scripts/verify.py
```

## Error handling

| Symptom | Cause | Fix |
|---|---|---|
| "unknown kid" | Response signed with a key not in current JWKS | Refresh JWKS cache; if persistent, the key may be rotated — check JWKS URL directly |
| "JWT signature invalid" | Payload tampered, or wrong public key | Confirm `kid` matches a JWKS entry, confirm algorithm pinned to ES256 |
| "JWT issuer mismatch" | Issuer claim doesn't match `https://api.insumermodel.com` | Confirm response actually came from InsumerAPI |
| "JWT expired" | Past its `exp` (30 min, or 5 with a delegation condition) | Re-request a fresh attestation; do not extend TTL |
| "conditionHash mismatch" | Condition object was modified after signing | Untrusted payload — reject |

## Related skills

| Skill | Purpose |
|---|---|
| `insumer-auth` | Get a key (verifying responses doesn't need a key, but requesting them does) |
| `insumer-attest` | Produces signed responses to verify |
| `insumer-trust` | Produces signed responses to verify |
| `insumer-trust-batch` | Verify each profile entry independently |

## References

- [jwks-format.md](references/jwks-format.md) — full JWKS document shape, key rotation policy, JWT claim list
- [`insumer-verify` on npm](https://www.npmjs.com/package/insumer-verify) — canonical raw-sig verification package
- [Public JWKS](https://insumermodel.com/.well-known/jwks.json) — fetch the live key set
- [JWT spec (RFC 7519)](https://datatracker.ietf.org/doc/html/rfc7519)
- [JWS spec (RFC 7515)](https://datatracker.ietf.org/doc/html/rfc7515)
