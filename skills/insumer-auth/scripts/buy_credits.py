#!/usr/bin/env python3
"""
Top up an existing InsumerAPI key with credits via on-chain payment.

Path 4 of 4 (see ../SKILL.md). Preserves key, history, tier, and integrations:
credits just increment. This script never sends funds: make the payment with
your own wallet, only after the user has approved the amount, token, chain and
recipient, then call this with its transaction hash. Sender must match the wallet registered to the
key (or pass --update-wallet to replace it).

Platform wallets:
  EVM:     0xAd982CB19aCCa2923Df8F687C0614a7700255a23
  Solana:  6a1mLjefhvSJX1sEX8PTnionbE9DqoYjU6F6bNkT4Ydr
  Bitcoin: bc1qg7qnerdhlmdn899zemtez5tcx2a2snc0dt9dt0
  Tron:    TC5yvwkAMakkXtUxYiu2Yn1xbBcwYuD6cn  (USDT-TRC20 only)

Payment chains (these ten and no others; funds sent on any other chain cannot
be recovered): USDC/USDT on Ethereum (1), Base (8453), Polygon (137),
Arbitrum (42161), Optimism (10), BNB Chain (56), Avalanche (43114) or Solana;
USDT-TRC20 on Tron; BTC on Bitcoin.

Volume discounts: $5–$99 → 25 credits per $1 ($0.04/credit),
                  $100–$499 → 33 credits per $1 (about $0.03/credit),
                  $500+ → 50 credits per $1 ($0.02/credit).

Usage:
    python buy_credits.py --tx 0xabc... --chain 8453 --amount 10
    python buy_credits.py --tx <tron-tx> --chain tron --amount 10
    python buy_credits.py --tx 0xabc... --chain 8453 --amount 100 --update-wallet
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

ENDPOINT = "https://api.insumermodel.com/v1/credits/buy"


def main() -> int:
    parser = argparse.ArgumentParser(description="Top up an InsumerAPI key with crypto.")
    parser.add_argument("--tx", required=True, help="Transaction hash proving payment")
    parser.add_argument("--chain", required=True, help="Payment chain: 1, 8453, 137, 42161, 10, 56, 43114, 'solana', 'tron' or 'bitcoin'")
    parser.add_argument("--amount", type=float, help="Stablecoin amount sent (min 5). Optional for BTC.")
    parser.add_argument("--update-wallet", action="store_true",
                        help="Replace the registered sender wallet with this transaction's sender")
    args = parser.parse_args()

    api_key = os.environ.get("INSUMER_API_KEY")
    if not api_key:
        print("INSUMER_API_KEY not set. See the insumer-auth skill.", file=sys.stderr)
        return 1

    chain = int(args.chain) if args.chain.isdigit() else args.chain

    body_dict = {
        "txHash": args.tx,
        "chainId": chain,
    }
    if args.amount is not None:
        body_dict["amount"] = args.amount
    if args.update_wallet:
        body_dict["updateWallet"] = True

    body = json.dumps(body_dict).encode("utf-8")

    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        return 1

    data = payload.get("data", {})
    print(f"\nCredits topped up")
    print(f"  Credits added:  {data.get('creditsAdded')}")
    print(f"  Total credits:  {data.get('totalCredits')}")
    print(f"  Paid (USD):     ${data.get('usdcPaid')} ({data.get('chainName')})\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
