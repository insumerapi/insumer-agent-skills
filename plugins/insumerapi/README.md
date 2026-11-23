# InsumerAPI plugin for Claude

InsumerAPI is wallet auth for AI agents. It answers one question: does this wallet meet this condition right now? The answer is a signed yes or no, and balances are never returned. Ask Claude things like "does this wallet hold at least 100 USDC on Base", "does it own an NFT from this collection", "is it a registered ERC-8004 agent", "build a trust profile for this wallet" or "what discount does this wallet get at this merchant".

Every result is signed twice: ES256 and a post-quantum ML-DSA-65 signature. Anyone can check it against the published keys without calling InsumerAPI again.

## Install

```
/plugin install insumerapi --marketplace insumerapi/insumer-agent-skills
```

## What it contains

**MCP server `insumer`** (`.mcp.json`): connects the hosted InsumerAPI MCP server at `https://api.insumermodel.com/mcp`. It needs no account and no API key. Its ten tools are the public signing keys, condition attestation, compliance templates, wallet trust profiles (single and batch), the merchant and token directories, a discount check and discount-code validation. None of them writes to a blockchain or moves funds. The server is shared, so the three tools that produce signed results (`insumer_attest`, `insumer_wallet_trust`, `insumer_batch_wallet_trust`) draw on a daily limit that resets at 00:00 UTC.

**Skills** (instructions only; no scripts):

| Skill | What it does |
|---|---|
| `insumer-hosted-tools` | How to call the ten hosted tools well: chain IDs, display-unit thresholds, reading the signed result, and what to do when the shared daily limit runs out |
| `insumer-jwks-verify` | How to verify a signed InsumerAPI response offline against the public keys, with code recipes for JavaScript and Python |

## Network endpoints and credentials

The plugin itself contacts one place: the hosted MCP server.

| Component | Calls | Sends |
| ------ | ----- | ----- |
| MCP server `insumer` | `https://api.insumermodel.com/mcp` | The tool arguments Claude passes: wallet addresses, conditions (chain, contract address, threshold), merchant IDs and discount codes |

The skills contain no code that runs on their own. The verification recipes in `insumer-jwks-verify`, if you choose to run them, fetch the public key set from `https://insumermodel.com/.well-known/jwks.json` and send nothing else.

The plugin reads no environment variables, asks for no API key and stores no credentials. It has no hooks. Nothing in it sends a transaction, makes a payment, signs anything with the user's wallet, or moves funds.

InsumerAPI does not store wallet addresses or conditions from verification requests. Privacy policy: https://insumermodel.com/privacy-policy/

## Links

- Documentation and REST API reference: https://insumermodel.com/developers/
- MCP server source (MIT): https://github.com/insumerapi/mcp-server-insumer
- Open-source verifier: `insumer-verify` on npm and PyPI
- Support: support@insumermodel.com

## Maintainers

These skills are built, not edited here. `insumer-hosted-tools` comes from the ChatGPT plugin repository (`insumer-chatgpt-plugin/skills/`) and `insumer-jwks-verify` from `skills/` at this repository's root, without its script. The few lines that point at skills this plugin does not carry are rewritten by `tools/sync-directory-plugin.sh`. Run it after any change to either source, and `tools/sync-directory-plugin.sh --check` before a release. Bump `version` in `.claude-plugin/plugin.json` on every change, because installed users are pinned to that version.

## License

MIT
