# InsumerAPI plugin for Claude

InsumerAPI is wallet auth for AI agents. It answers one question: does this wallet meet this condition right now? The answer is a signed yes or no, and balances are never returned. Ask Claude things like "does this wallet hold at least 100 USDC on Base", "does it own an NFT from this collection", "is it a registered ERC-8004 agent", "build a trust profile for this wallet" or "what discount does this wallet get at this merchant".

Every result is signed twice: ES256 and a post-quantum ML-DSA-65 signature. Anyone can check it against the published keys without calling InsumerAPI again.

## Install

```
/plugin install insumerapi --marketplace insumerapi/insumer-agent-skills
```

## What it contains

**MCP server `insumer`** (`.mcp.json`): connects the hosted InsumerAPI MCP server at `https://api.insumermodel.com/mcp`. It needs no account and no API key. Its ten tools are the public signing keys, condition attestation, compliance templates, wallet trust profiles (single and batch), the merchant and token directories, a discount check and discount-code validation. None of them writes to a blockchain or moves funds. The server is shared, so the three tools that produce signed results (`insumer_attest`, `insumer_wallet_trust`, `insumer_batch_wallet_trust`) draw on a daily limit that resets at 00:00 UTC.

**Skills:**

| Skill | What it does |
|---|---|
| `insumer-hosted-tools` | How to use the ten hosted tools, and when to switch to the REST skills with your own key |
| `insumer-attest` | Signed yes/no on wallet conditions through the REST API |
| `insumer-trust` | Signed wallet trust profile for one wallet |
| `insumer-trust-batch` | Signed trust profiles for up to ten wallets |
| `insumer-jwks-verify` | Offline verification of signed responses against the public keys |
| `insumer-discount` | Token-holder discounts at InsumerAPI merchants |
| `insumer-auth` | Getting an API key (free with an email address) and topping it up |

## Network endpoints and credentials

Everything this plugin contacts is run by InsumerAPI, at `api.insumermodel.com` or `insumermodel.com`. There are no hooks and no install steps. The scripts use the Python standard library, except `insumer-jwks-verify/scripts/verify.py`, which needs `pip install 'pyjwt[crypto]'`.

| Component | Calls | Sends |
| ------ | ----- | ----- |
| MCP server `insumer` | `https://api.insumermodel.com/mcp` | The tool arguments Claude passes: wallet addresses, conditions (chain, contract address, threshold), merchant IDs and discount codes |
| `insumer-auth/scripts/create_key.py` | `POST https://api.insumermodel.com/v1/keys/create` | `email` (yours), `appName`, `tier: "free"`; no key needed |
| `insumer-auth/scripts/buy_key.py` | `POST https://api.insumermodel.com/v1/keys/buy` | `txHash`, `chainId`, `amount` (USDC), `appName` (default `"insumer-agent-skills"`), `keyDelivery: "apiKey"`, and the `senderSignature` you pass in `--sender-signature`; no key needed |
| `insumer-auth/scripts/buy_credits.py` | `POST https://api.insumermodel.com/v1/credits/buy` | `INSUMER_API_KEY`, plus `txHash`, `chainId`, `amount` (USDC), optional `updateWallet`, and the `senderSignature` you pass in `--sender-signature` when one is needed |
| `insumer-attest/scripts/attest.py` | `POST https://api.insumermodel.com/v1/attest` | `INSUMER_API_KEY` and the request body you provide |
| `insumer-trust/scripts/trust.py` | `POST https://api.insumermodel.com/v1/trust` | `INSUMER_API_KEY`, the wallet addresses you pass, and optional `proof: "merkle"` |
| `insumer-trust-batch/scripts/trust_batch.py` | `POST https://api.insumermodel.com/v1/trust/batch` | `INSUMER_API_KEY`, the wallet addresses you pass, and optional `proof: "merkle"`. It always saves the signed response to a local JSON file (`--out`, default `trust_batch_<time>.json` in the working directory) |
| `insumer-jwks-verify/scripts/verify.py` | `GET https://insumermodel.com/.well-known/jwks.json` | Nothing; it fetches the public keys and verifies locally |
| `insumer-discount/scripts/proof_message.py` | Nothing | Nothing; it prints a message for the wallet to sign. It never signs and never handles a key |
| `insumer-discount/scripts/discount.py` | `GET https://api.insumermodel.com/v1/merchants/{id}`, `GET .../v1/discount/check`, and with `--create`, `POST .../v1/verify` | The merchant ID and wallet address you pass; with `--create`, also `INSUMER_API_KEY` and the signed proof you pass in `--proof-file` |

The only credential is your own `INSUMER_API_KEY`, read from the environment and sent only to `api.insumermodel.com` in the `X-API-Key` header. The hosted MCP server needs no key at all. No script signs or sends a transaction or holds a private key. None reads any other environment variable (beyond the standard proxy variables Python's HTTP client honors) or any file except a request, wallet list or signed proof you pass on the command line (`--body-file`, `--wallets-file`, `--proof-file`) or on stdin.

**Payments need your approval.** The paid paths in `insumer-auth` (buying a key or credits) begin with a USDC payment that you make from your own wallet. The skill tells Claude never to send or prepare a payment unless you have confirmed the amount, token, chain and recipient address in that session. Where the API asks for it, the wallet that paid also signs a short text confirming it sent the payment; you sign it with your own wallet, and no script signs it. The free path (a key from an email address) involves no payment.

`create_key.py` and `buy_key.py` send `appName: "insumer-agent-skills"` by default, a label on the key that tells InsumerAPI which channel it came from. Pass `--app-name` to use your own; nothing else is collected.

InsumerAPI does not store wallet addresses or conditions from verification requests. Privacy policy: https://insumermodel.com/privacy-policy/

## Links

- Documentation: https://insumermodel.com/developers/
- MCP server source (MIT): https://github.com/insumerapi/mcp-server-insumer
- Open-source verifier: `insumer-verify` on npm and PyPI
- Support: support@insumermodel.com

## Maintainers

These skills are copies. Edit the six REST skills under `skills/` at the repository root; `insumer-hosted-tools` lives in the ChatGPT plugin repository (`insumer-chatgpt-plugin/skills/`). Run `tools/sync-directory-plugin.sh` after any change, and `tools/sync-directory-plugin.sh --check` before a release. Bump `version` in `.claude-plugin/plugin.json` on every change, because installed users are pinned to that version.

## License

MIT
