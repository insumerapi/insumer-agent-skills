# Insumer Agent Skills

**Wallet auth as agent skills.** Install once, and every Claude Code, Cursor, Copilot, Codex, Gemini CLI, and 25+ other [agentskills.io](https://agentskills.io)-compatible agent gets native knowledge of how to call [InsumerAPI](https://insumermodel.com) for condition-based access across 37 chains.

> **Boolean, not balance. Verified yes or no. Provable and private.**

> [!NOTE]
> **Technical preview**
>
> These skills are in early release. Expect refinements as the API surface evolves and as we add coverage for new chains and condition types.

---

## What is wallet auth?

OAuth proves who the user is. **Wallet auth proves what the wallet holds.** InsumerAPI evaluates a wallet's on-chain state against a condition and returns an ES256-signed, JWKS-verifiable boolean. The pattern is **read → evaluate → sign**:

1. **Read** — InsumerAPI reads the wallet's on-chain state on the requested chain
2. **Evaluate** — wallet state is checked against the condition
3. **Sign** — a boolean result is returned, ES256-signed, with a `conditionHash` for tamper detection

**No secrets. No identity-first. No static credentials.** Token gating is one form of condition-based access; this is the general primitive.

## Available skills

| Skill | What it does | Version |
| ----- | ------------ | ------- |
| [insumer-auth](skills/insumer-auth/) | Free API key creation, env var setup, credit balance | 0.2.0 |
| [insumer-attest](skills/insumer-attest/) | Custom condition attestation across 37 chains (`/v1/attest`) | 0.2.0 |
| [insumer-trust](skills/insumer-trust/) | Curated wallet trust profile, 145 base checks across 27 chains (`/v1/trust`) | 0.2.0 |
| [insumer-trust-batch](skills/insumer-trust-batch/) | Batch trust profiles for multiple wallets (`/v1/trust/batch`) | 0.2.0 |
| [insumer-jwks-verify](skills/insumer-jwks-verify/) | Offline ES256 verification of signed responses (raw `sig` or JWT) against the public JWKS | 0.2.0 |
| [insumer-discount](skills/insumer-discount/) | Token-holder discounts at InsumerAPI merchants: read the store's terms, prove the wallet if it pays, create a signed code (`/v1/verify`) | 0.1.0 |

---

## Installation

These skills follow the [Agent Skills](https://agentskills.io) open standard, so they install into any compatible agent.

### Option A: Using the `skills` CLI (recommended)

```bash
# Project-level (per repo)
npx skills add insumerapi/insumer-agent-skills

# Global (every project on your machine)
npx skills add insumerapi/insumer-agent-skills --global
```

### Option B: Manual (Claude Code)

Each skill folder goes directly under `~/.claude/skills/` (one level deep; a nested `insumer/` group folder is not discovered):

```bash
git clone https://github.com/insumerapi/insumer-agent-skills.git
mkdir -p ~/.claude/skills
cp -r insumer-agent-skills/skills/insumer-* ~/.claude/skills/
```

### Option C: Manual (Grok Build)

Grok Build reads the same `SKILL.md` format from `~/.grok/skills/` (every project) or `.grok/skills/` in a repo:

```bash
git clone https://github.com/insumerapi/insumer-agent-skills.git
mkdir -p ~/.grok/skills
cp -r insumer-agent-skills/skills/insumer-* ~/.grok/skills/
```

Restart your agent. The skills activate when you ask about InsumerAPI: getting a key, attesting a wallet condition, a wallet trust profile, or verifying an InsumerAPI signed response.

---

## First use (60 seconds)

1. **Get a free API key** (10 free verifications plus 100 reads/day, no signup beyond an email):

   ```bash
   curl -s -X POST https://api.insumermodel.com/v1/keys/create \
     -H "Content-Type: application/json" \
     -d '{"email":"you@example.com","appName":"insumer-agent-skills","tier":"free"}'
   ```

2. **Set the env var:**

   ```bash
   export INSUMER_API_KEY='insr_live_...'
   ```

3. **Ask your agent something that triggers a skill.** Examples:

   - "Add wallet auth to my Express app — gate `/admin` by USDC balance on Base"
   - "Check whether wallet `0xabc...def` holds at least 100 USDC on Base"
   - "Show me a wallet trust profile for `0xd8dA...6045`"
   - "Verify this JWT against the InsumerAPI JWKS"

The skill loads the right canonical request shape, the offline verification recipe, and the failure-mode guardrails — your agent emits working integration code on the first try.

---

## Why these skills exist

The agent ecosystem already knows how to *call* HTTP APIs. What it doesn't know — and gets wrong — is the InsumerAPI-specific patterns that matter:

- **Boolean, not balance** by construction (standard mode never returns the underlying balance)
- **Offline ES256 verification** against the public JWKS (the signature is the product, not the JSON body)
- **`decimals` is a cross-check, never an input** (leave it out: the token's own decimals are read from the chain, and a sent value that differs is rejected with a `400`)
- **Backend-only key handling** (never expose `insr_live_...` in browser JS)
- **Read → evaluate → sign** primitive (the whole point — not just an HTTP call)

Each skill encodes these as hard constraints, with reference shapes verified against the live API.

---

## Compatible agents

These skills work in any [agentskills.io](https://agentskills.io)-compatible agent. The current adopter list includes Claude, Claude Code, Cursor, GitHub Copilot, VS Code, OpenAI Codex, Google Gemini CLI, JetBrains Junie, Sourcegraph Amp, Block Goose, OpenHands, OpenCode, Letta, Roo Code, Mistral Vibe, ByteDance Trae, Snowflake Cortex, Databricks Genie, Spring AI, Kiro, Workshop, Qodo, Factory, Firebender, and others — see [agentskills.io/home](https://agentskills.io/home) for the live list. xAI's Grok Build reads the same `SKILL.md` format (see Option C above).

---

## Network endpoints and credentials

The skills are instructions plus small helper scripts. There are no hooks, no MCP servers, and no install or postinstall steps. The scripts use the Python standard library, except `insumer-jwks-verify/scripts/verify.py`, which needs `pyjwt[crypto]` installed by you.

| Script | Calls | Sends |
| ------ | ----- | ----- |
| `insumer-auth/scripts/create_key.py` | `POST https://api.insumermodel.com/v1/keys/create` | `email` (yours), `appName`, `tier: "free"`; no key needed |
| `insumer-auth/scripts/buy_key.py` | `POST https://api.insumermodel.com/v1/keys/buy` | `txHash`, `chainId`, `appName` (default `"insumer-agent-skills"`), `keyDelivery: "apiKey"`, and `amount` unless paying in BTC; no key needed |
| `insumer-auth/scripts/buy_credits.py` | `POST https://api.insumermodel.com/v1/credits/buy` | `INSUMER_API_KEY`, plus `txHash`, `chainId`, `amount` unless paying in BTC, optional `updateWallet` |
| `insumer-attest/scripts/attest.py` | `POST https://api.insumermodel.com/v1/attest` | `INSUMER_API_KEY` and the request body you provide |
| `insumer-trust/scripts/trust.py` | `POST https://api.insumermodel.com/v1/trust` | `INSUMER_API_KEY`, the wallet addresses you pass, and optional `proof: "merkle"` |
| `insumer-trust-batch/scripts/trust_batch.py` | `POST https://api.insumermodel.com/v1/trust/batch` | `INSUMER_API_KEY`, the wallet addresses you pass, and optional `proof: "merkle"` |
| `insumer-jwks-verify/scripts/verify.py` | `GET https://insumermodel.com/.well-known/jwks.json` | Nothing; it fetches the public keys and verifies locally |
| `insumer-discount/scripts/proof_message.py` | Nothing | Nothing; it prints a message for the wallet to sign. It never signs and never handles a key |
| `insumer-discount/scripts/discount.py` | `GET https://api.insumermodel.com/v1/merchants/{id}`, `GET .../v1/discount/check`, and with `--create`, `POST .../v1/verify` | The merchant ID and wallet address you pass; with `--create`, also `INSUMER_API_KEY` and the signed proof you pass in `--proof-file` |

The only credential is `INSUMER_API_KEY`, read from the environment and sent only to `api.insumermodel.com` in the `X-API-Key` header. No script signs or sends a transaction or holds a private key. None reads any other environment variable (beyond the standard proxy variables Python's HTTP client honors) or any file except a request, wallet list or signed proof you pass on the command line (`--body-file`, `--wallets-file`, `--proof-file`) or on stdin.

`create_key.py` and `buy_key.py` send `appName: "insumer-agent-skills"` by default, a label on the key that tells InsumerAPI which channel it came from. Pass `--app-name` to use your own; nothing else is collected.

The skills also show `GET https://api.insumermodel.com/v1/credits` (balance check) as a `curl` example. The paid paths in `insumer-auth` (Path 3 and Path 4) begin with a crypto payment that the skill tells the agent never to make without the user's explicit approval of the amount, token, chain and recipient.

---

## Resources

- **InsumerAPI homepage**: <https://insumermodel.com>
- **OpenAPI spec**: <https://insumermodel.com/openapi.yaml>
- **Public JWKS**: <https://insumermodel.com/.well-known/jwks.json>
- **Developer docs**: <https://insumermodel.com/developers/api-reference/>
- **Pricing & paid tiers**: <https://insumermodel.com/developers/account/>
- **MCP server (alternative agent surface)**: [`mcp-server-insumer`](https://github.com/insumerapi/mcp-server-insumer)

## License

MIT — see [LICENSE](LICENSE).
