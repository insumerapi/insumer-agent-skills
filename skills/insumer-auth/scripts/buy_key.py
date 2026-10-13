#!/usr/bin/env python3
"""
Buy an InsumerAPI key with USDC, USDT, or BTC (agent-onboarding path).

Path 3 of 4 (see ../SKILL.md). No email required: sender wallet from the
on-chain transaction becomes the key's identity. This script never sends
funds: make the payment with your own wallet, only after the user has approved
the amount, token, chain and recipient, then call this with its transaction hash.

It sends keyDelivery "apiKey" so the key string is returned. With the API's
default ("wallet"), an EVM purchase that issues an Insumer Access pass to the
paying wallet returns no key: that wallet authenticates with Authorization: Wallet
instead.

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

appName defaults to "insumer-agent-skills", a label on the key that tells
InsumerAPI which channel the key came from. Pass --app-name to use your own.

Usage:
    python buy_key.py --tx 0xabc... --chain 8453 --amount 10
    python buy_key.py --tx <tron-tx> --chain tron --amount 10
    python buy_key.py --tx <btc-tx> --chain bitcoin
    python buy_key.py --tx 0xabc... --chain 8453 --amount 10 --app-name my-custom-name
"""
import argparse
import json
import sys
import urllib.request
import urllib.error

ENDPOINT = "https://api.insumermodel.com/v1/keys/buy"
DEFAULT_APP_NAME = "insumer-agent-skills"


def main() -> int:
    parser = argparse.ArgumentParser(description="Buy an InsumerAPI key with crypto.")
    parser.add_argument("--tx", required=True, help="Transaction hash proving payment")
    parser.add_argument("--chain", required=True, help="Payment chain: 1, 8453, 137, 42161, 10, 56, 43114, 'solana', 'tron' or 'bitcoin'")
    parser.add_argument("--amount", type=float, help="Stablecoin amount sent (min 5). Optional for BTC.")
    parser.add_argument("--app-name", default=DEFAULT_APP_NAME,
                        help=f"App name (default: {DEFAULT_APP_NAME!r})")
    args = parser.parse_args()

    chain = int(args.chain) if args.chain.isdigit() else args.chain

    body_dict = {
        "txHash": args.tx,
        "chainId": chain,
        "appName": args.app_name,
        "keyDelivery": "apiKey",
    }
    if args.amount is not None:
        body_dict["amount"] = args.amount

    body = json.dumps(body_dict).encode("utf-8")

    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json"},
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
    key = data.get("key")
    if not key:
        print("Unexpected response:", json.dumps(payload, indent=2), file=sys.stderr)
        return 1

    print(f"\nKey purchased for {data.get('registeredWallet')}")
    print(f"  Tier:           {data.get('tier')}")
    print(f"  Daily limit:    {data.get('dailyLimit')}")
    print(f"  Credits added:  {data.get('creditsAdded')}")
    print(f"  Total credits:  {data.get('totalCredits')}")
    if data.get("btcPaid") is not None:
        print(f"  BTC paid:       {data.get('btcPaid')} BTC (${data.get('usdEquivalent')})")
    else:
        print(f"  Paid:           ${data.get('usdcPaid')} ({data.get('chainName')})")
    print(f"  Effective rate: {data.get('effectiveRate')}")
    print(f"\nStore this key securely (shown only once):\n")
    print(f"    export INSUMER_API_KEY='{key}'\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
