# Insumer

Agent skills for [InsumerAPI](https://insumermodel.com): wallet auth and condition-based access across 37 chains. Boolean, not balance. Read → evaluate → sign.

## Skills

| Skill | Description | Version | Author |
| ----- | ----------- | ------- | ------ |
| [insumer-auth](insumer-auth/) | Free API key creation, env var setup, credit balance | 0.2.0 | InsumerAPI |
| [insumer-attest](insumer-attest/) | Custom condition attestation (`/v1/attest`) | 0.2.0 | InsumerAPI |
| [insumer-trust](insumer-trust/) | Curated wallet trust profile (`/v1/trust`) | 0.2.0 | InsumerAPI |
| [insumer-trust-batch](insumer-trust-batch/) | Batch trust profiles (`/v1/trust/batch`) | 0.2.0 | InsumerAPI |
| [insumer-jwks-verify](insumer-jwks-verify/) | Offline ES256 verification against the public JWKS | 0.2.0 | InsumerAPI |
| [insumer-discount](insumer-discount/) | Token-holder discounts: store terms, optional wallet proof, signed code (`/v1/verify`) | 0.1.0 | InsumerAPI |

Each skill includes a `scripts/` folder with request helpers; some also include a `references/` folder with detailed shapes and reference values.

## Get started

Set the API key once (created via the `insumer-auth` skill):

```bash
export INSUMER_API_KEY='insr_live_...'
```

Then ask your agent something that triggers any of the skills above. They auto-activate based on the user's request — no manual invocation needed.

## API base

All skills assume the public API base:

```
https://api.insumermodel.com
```

## Verification

Every signed response is verifiable offline against the public JWKS at:

```
https://insumermodel.com/.well-known/jwks.json
```

The signing key never leaves the issuer; the verifier needs only the public key. See [`insumer-jwks-verify`](insumer-jwks-verify/) for the canonical recipe.
