---
name: insumer-x402-recipes
description: >
  Recipes for agents that pay per call over x402 and should check a wallet
  with InsumerAPI before they spend: send a gift card or other reward only to
  members, check what an agent holds before hiring it, enforce a holding rule
  written in dollars, learn what people say about a wallet and what it holds,
  or buy paid research only for wallets that qualify. Use when the user wants
  an agent to pay another x402 service only after a signed yes or no about a
  wallet, or asks for the Agentic Cookbook for x402. Every recipe ran for real
  on Base; the payments are public.
metadata:
  version: "0.1.0"
  author: InsumerAPI
---

# The Agentic Cookbook for x402

**x402 moves the money. InsumerAPI checks the conditions.** Each recipe pairs an x402 service with an InsumerAPI check, so the agent acts on a signed answer and keeps it. All five ran for real on Base on 10 November 2026. The page with every payment on Basescan, two published signed answers and a runnable script: https://insumermodel.com/x402-cookbook/

Every InsumerAPI answer is signed twice: ES256 and a post-quantum ML-DSA-65 signature. Anyone can verify it against `https://insumermodel.com/.well-known/jwks.json`.

## Rules for every recipe

1. **Check first, then spend.** Where a no should stop the agent, the InsumerAPI call comes first. A no ends the recipe and nothing more is spent.
2. **Check the right wallet.** If the policy checks the paying wallet, use the verified x402 payer address of the request the agent received. If it checks a different wallet, require a signed challenge from that wallet first. Never trust an address the requester only typed in. Checking a wallet's holdings does not prove who controls it.
3. **Verify before acting.** Send `"format": "jwt"` so the wallet is signed as the JWT `sub` claim, then verify the answer offline (see `insumer-jwks-verify`). Act only when the signatures verify, the post-quantum verdict is `verified` (not merely `unverifiable`: `valid` can be true without it), `sub` equals the wallet you meant to check, and `pass` is `true`. Verify against a saved copy of the JWKS so the check is offline. Read the verdicts one by one: every answer expires 30 minutes after it was signed, so an older answer reads `valid: false` even though both signatures still verify.
4. **Payments need approval.** Never pay without the user's explicit approval of the amount, token, chain and recipient, or a standing cap the user set. Pay only the payee in the service's own 402 quote, only USDC on the expected network, and refuse a price above the cap. When comparing addresses, normalize each one on its own: in viem, `list.map((a) => getAddress(a))`, never `list.map(getAddress)`, which passes the array index as a chain ID and changes the checksum.
5. **Keep the signed answer** with the payment record. `meta.settlementTx` in an InsumerAPI response names the payment that bought it, but it is payment metadata outside the signed attestation: check it against the chain, not against the signature.
6. **Prices for other services** are what each charged on 10 November 2026. The live 402 quote is the price; read it before every payment.

The InsumerAPI calls below use an API key (`insumer-auth`) through the helper scripts in `insumer-attest` and `insumer-trust`. They also work with no key over x402: the call answers `402` with a quote ($0.05 for `/v1/attest`, $0.15 for `/v1/trust`), payable in USDC on Base, Polygon, Arbitrum, Arc or Solana. The other services are paid with the agent's own x402 client.

## Recipe 1: Send a real-world reward only to members

**Outcome:** an agent gives a gift card, eSIM or phone top-up only to members whose wallets meet a rule: a member pass (for example one issued by Skye Meta's Bothy), an NFT, or a number of tokens.

1. The member signs a one-time challenge with their wallet; the agent verifies the signature.
2. InsumerAPI `POST /v1/attest` with that wallet and the rule. A no ends the recipe.
3. Bitrefill `GET https://api.bitrefill.com/x402/gift-cards/search?q=...&country=...` ($0.002): find the reward.
4. Bitrefill `POST https://api.bitrefill.com/x402/invoice/create` ($0.002), body `{"items":[{"product_id":"...","package_value":"5"}]}`: lock the price.
5. Bitrefill `POST https://api.bitrefill.com/x402/invoice/pay` (the reward's price), body `{"invoice_id":"..."}`.
6. Bitrefill `GET https://api.bitrefill.com/x402/invoice/status?invoice_id=...`: sign in with the wallet that paid (the response carries a sign-in challenge) and collect the code, then send it privately to the member. Never log or store the code.

```json
{
  "wallet": "0xMEMBER_WALLET",
  "format": "jwt",
  "conditions": [{
    "type": "token_balance", "chainId": 8453,
    "contractAddress": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "threshold": "1", "label": "Holds 1 USDC on Base"
  }]
}
```

For a pass or any other NFT, use `"type": "nft_ownership"` with the contract address. In the run, a $5 Amazon.com card cost $5.25, and the code was released about 3 seconds after payment.

## Recipe 2: Check what an agent holds before hiring it

**Outcome:** before paying another agent for a job, the agent confirms it is a registered ERC-8004 agent and, at that moment, holds a set multiple of the job's value. It is a check at one moment, not a bond or escrow.

1. trust-agent.io `GET https://trust-agent.io/v1/reputation?chain=base&subject=AGENT_ID` ($0.002): ERC-8004 reviews, with reviewers that share a funder counted once.
2. InsumerAPI `POST /v1/attest` with the agent owner's wallet and two conditions. A no means do not hire.
3. Pay for the job over x402, or walk away.

```json
{
  "wallet": "0xAGENT_OWNER_WALLET",
  "format": "jwt",
  "conditions": [
    { "type": "erc8004_agent", "chainId": 8453, "agentId": "AGENT_ID",
      "label": "Owns the ERC-8004 agent" },
    { "type": "ratio_to_amount", "chainId": 8453,
      "contractAddress": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "multiple": "10", "amount": "1",
      "label": "Holds 10x a $1 job in USDC" }
  ]
}
```

`erc8004_agent` passes for the agent's owner or for the wallet the registry binds to the agent. If the rule is ownership, also require `"matchedVia": "owner"` in that condition's result. In the run, the reviews looked healthy (50 reviews from 25 separate clients, none flagged) and the answer was still no: the owner did not hold 10 times the job.

## Recipe 3: Enforce a rule written in dollars

**Outcome:** the agent enforces "holds at least $100 of WETH" and gets a signed yes or no.

1. CoinGecko `GET https://pro-api.coingecko.com/api/v3/x402/onchain/simple/networks/base/token_price/TOKEN` ($0.005): today's price.
2. Divide the dollar rule by the price and **round up** to the token's decimals, so the threshold is never below the rule. Send it as a decimal string.
3. InsumerAPI `POST /v1/attest` with `token_balance` and that threshold. Put the price in the `label`: the label is carried inside the signed answer. Keep the CoinGecko response as the source of the price.

In the run, WETH was $2,065.25, so the threshold was `0.0484202881007142` (rounded up to 18 decimals).

## Recipe 4: Learn what people say about a wallet, and what it holds

**Outcome:** before dealing with a wallet, the agent has its standing with people and signed facts about its holdings.

1. Ethos `GET https://developers.ethos.network/x402/user/address/WALLET` ($0.001): profile, linked X account and a credibility score built from reviews and vouches.
2. InsumerAPI `POST /v1/trust` with `{"wallet": "0xWALLET"}`: a signed fact profile across 10 dimensions. No score, no opinion, just cryptographically verifiable evidence organized by dimension. See `insumer-trust`.

## Recipe 5: Buy research only for wallets that qualify

**Outcome:** an agent that offers paid search or data spends on it only when the requesting wallet meets the rule.

1. InsumerAPI `POST /v1/attest` with the requesting wallet (see rule 2). A no ends the recipe.
2. Verify the answer offline and confirm the JWT `sub` is the requesting wallet (rule 3).
3. Exa `POST https://api.exa.ai/search` ($0.007), body `{"query":"...","numResults":5,"type":"auto"}`. Any paid search or data service on x402 fits here.

The whole recipe in one runnable file, tested end to end on Base: https://insumermodel.com/x402-cookbook/recipe-5.mjs (`npm install viem insumer-verify @noble/post-quantum`, then save the keys once with `curl -o jwks.json https://insumermodel.com/.well-known/jwks.json`; `--dry` quotes and signs without sending). It caps each payment, pays only the expected payees, verifies offline against the saved keys, requires a verified ML-DSA-65 signature, and only then spends.

## Related skills

| Skill | Purpose |
|---|---|
| `insumer-auth` | API key creation and top-up |
| `insumer-attest` | The condition check every recipe uses (`/v1/attest`) |
| `insumer-trust` | The fact profile in recipe 4 (`/v1/trust`) |
| `insumer-jwks-verify` | Offline verification of the signed answer, including the post-quantum signature |

## References

- [The Agentic Cookbook for x402](https://insumermodel.com/x402-cookbook/)
- [Published signed answer, recipe 5](https://insumermodel.com/x402-cookbook/evidence/recipe-5-attestation.json)
- [InsumerAPI OpenAPI spec](https://insumermodel.com/openapi.yaml)
- [Public JWKS](https://insumermodel.com/.well-known/jwks.json)
