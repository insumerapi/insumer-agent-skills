#!/usr/bin/env python3
"""
Top up an existing InsumerAPI key with credits via an on-chain USDC payment.

Path 4 of 4 (see ../SKILL.md). Preserves key, history, tier, and integrations:
credits just increment. This script never sends funds and never signs: make the
payment with your own wallet, only after the user has approved the amount,
token, chain and recipient, then call this with its transaction hash. Sender
must match the wallet registered to the key (or pass --update-wallet to replace
it).

Purchases are paid in USDC only. Platform wallets:
  USDC on Ethereum, Base, Polygon, Arbitrum, Optimism or Avalanche:
           0xee432065474D2C852700f74e3fD81e2Bcc16a3D4
  USDC on BNB Chain:
           0xAd982CB19aCCa2923Df8F687C0614a7700255a23
           (this previous address also still takes USDC on the other EVM
           chains during the changeover; it takes no USDT)
  USDC on Solana: 8fyEGM5tRjMocKQWaVXyM2XvvnTxR3sWdrYtug2zeLX4
           (the previous Solana address 6a1mLjefhvSJX1sEX8PTnionbE9DqoYjU6F6bNkT4Ydr
           still takes USDC during the changeover; it takes no USDT)

Payment chains (USDC on these eight and no others; funds sent on any other
chain cannot be recovered): Ethereum (1), Base (8453), Polygon (137),
Arbitrum (42161), Optimism (10), BNB Chain (56), Avalanche (43114) or Solana.
Payments on Bitcoin or Tron, and USDT or any other token, are refused with a 400.

Sender signature: needed only when the payment registers a wallet to the key,
that is when the key has no registered wallet yet, or with --update-wallet from
a different wallet. A top-up from the wallet already registered needs none.
The wallet that sent the payment signs this exact text (five lines joined by
\\n, no trailing newline) and the signature goes in --sender-signature:

    api.insumermodel.com
    Confirm the wallet that sent this payment.
    Purpose: credit purchase
    Chain: eip155:8453            (eip155:<chainId>, or: solana)
    Transaction: <transaction id> (EVM: 0x + lowercase hex; Solana: as given)

If it is needed and missing, the API answers 400 with the exact text, the
script prints it, and the payment is not used. Sign it with the paying wallet
(EVM: EIP-191 personal_sign, 0x hex, smart-contract wallets accepted; Solana:
signMessage over the UTF-8 text, base58 or base64), then run the same command
again with --sender-signature.

Volume discounts: $5–$99 → 25 credits per $1 ($0.04/credit),
                  $100–$499 → 33 credits per $1 (about $0.03/credit),
                  $500+ → 50 credits per $1 ($0.02/credit).

Usage:
    python buy_credits.py --tx 0xabc... --chain 8453 --amount 10
    python buy_credits.py --tx <solana-tx> --chain solana --amount 10
    python buy_credits.py --tx 0xabc... --chain 8453 --amount 100 --update-wallet --sender-signature 0x...
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

ENDPOINT = "https://api.insumermodel.com/v1/credits/buy"
SIGN_TEXT_FIRST_LINE = "api.insumermodel.com\n"


def text_to_sign(message):
    """Return the text to sign carried in an API error message, or None."""
    if not isinstance(message, str):
        return None
    _, sep, tail = message.partition("\n\n")
    if sep and tail.startswith(SIGN_TEXT_FIRST_LINE):
        return tail
    return None


def print_sign_instructions(status, message, text):
    print(f"HTTP {status}: {message.partition(chr(10))[0]}", file=sys.stderr)
    print("\nThe wallet that sent the payment must sign this exact text "
          "(five lines, no trailing newline):\n", file=sys.stderr)
    print("-----BEGIN TEXT-----", file=sys.stderr)
    print(text, file=sys.stderr)
    print("-----END TEXT-----", file=sys.stderr)
    print("\nThe same text as a JSON string, with the line breaks written as \\n:",
          file=sys.stderr)
    print(f"    {json.dumps(text)}", file=sys.stderr)
    print("\nHow to sign it:", file=sys.stderr)
    print("  EVM:    EIP-191 personal_sign (the wallet's \"sign message\"); send the 0x hex"
          " signature. Smart-contract wallets (ERC-1271) are accepted.", file=sys.stderr)
    print("  Solana: the wallet's signMessage over the UTF-8 text; send the signature in"
          " base58 or base64.", file=sys.stderr)
    print("Signing moves no funds, but it is the user's wallet: show the user the text"
          " before it is signed.", file=sys.stderr)
    print("\nThis payment has not been used. Run the same command again with"
          " --sender-signature <signature>.", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Top up an InsumerAPI key with USDC.")
    parser.add_argument("--tx", required=True, help="Transaction hash proving payment")
    parser.add_argument("--chain", required=True,
                        help="Payment chain (USDC only): 1, 8453, 137, 42161, 10, 56, 43114 or 'solana'")
    parser.add_argument("--amount", type=float, required=True,
                        help="USDC amount sent (minimum 5)")
    parser.add_argument("--update-wallet", action="store_true",
                        help="Replace the registered sender wallet with this transaction's sender "
                             "(needs --sender-signature from the new wallet)")
    parser.add_argument("--sender-signature",
                        help="Signature by the paying wallet over the text the API returns. Needed when "
                             "the key has no registered wallet yet, or with --update-wallet.")
    args = parser.parse_args()

    api_key = os.environ.get("INSUMER_API_KEY")
    if not api_key:
        print("INSUMER_API_KEY not set. See the insumer-auth skill.", file=sys.stderr)
        return 1

    chain = int(args.chain) if args.chain.isdigit() else args.chain

    body_dict = {
        "txHash": args.tx,
        "chainId": chain,
        "amount": args.amount,
    }
    if args.update_wallet:
        body_dict["updateWallet"] = True
    if args.sender_signature:
        body_dict["senderSignature"] = args.sender_signature

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
        raw = e.read().decode("utf-8", errors="replace")
        try:
            message = json.loads(raw).get("error", {}).get("message")
        except (ValueError, AttributeError):
            message = None
        text = text_to_sign(message)
        if e.code in (400, 403) and text:
            print_sign_instructions(e.code, message, text)
            return 2
        print(f"HTTP {e.code}: {raw}", file=sys.stderr)
        return 1

    data = payload.get("data", {})
    print(f"\nCredits topped up")
    print(f"  Credits added:  {data.get('creditsAdded')}")
    print(f"  Total credits:  {data.get('totalCredits')}")
    print(f"  Paid:           ${data.get('usdcPaid')} USDC ({data.get('chainName')})\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
