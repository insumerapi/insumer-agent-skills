#!/usr/bin/env python3
"""
Buy an InsumerAPI key with USDC (agent-onboarding path).

Path 3 of 4 (see ../SKILL.md). No email required: the wallet that sent the
on-chain payment becomes the key's identity, and it signs a short text to
confirm it sent the payment. This script never sends funds and never signs:
make the payment with your own wallet, only after the user has approved the
amount, token, chain and recipient, then call this with its transaction hash.

It sends keyDelivery "apiKey" so the key string is returned. With the API's
default ("wallet"), an EVM purchase that issues an Insumer Access pass to the
paying wallet returns no key: that wallet authenticates with Authorization: Wallet
instead.

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

Sender signature: the wallet that sent the payment signs this exact text (five
lines joined by \\n, no trailing newline) and the signature goes in
--sender-signature:

    api.insumermodel.com
    Confirm the wallet that sent this payment.
    Purpose: key purchase
    Chain: eip155:8453            (eip155:<chainId>, or: solana)
    Transaction: <transaction id> (EVM: 0x + lowercase hex; Solana: as given)

Run the script once without --sender-signature: the API answers 400 with the
exact text, the script prints it, and the payment is not used. Sign it with the
paying wallet (EVM: EIP-191 personal_sign, 0x hex, smart-contract wallets
accepted; Solana: signMessage over the UTF-8 text, base58 or base64), then run
the same command again with --sender-signature.

Volume discounts: $5–$99 → 25 credits per $1 ($0.04/credit),
                  $100–$499 → 33 credits per $1 (about $0.03/credit),
                  $500+ → 50 credits per $1 ($0.02/credit).

appName defaults to "insumer-agent-skills", a label on the key that tells
InsumerAPI which channel the key came from. Pass --app-name to use your own.

Usage:
    python buy_key.py --tx 0xabc... --chain 8453 --amount 10
    python buy_key.py --tx 0xabc... --chain 8453 --amount 10 --sender-signature 0x...
    python buy_key.py --tx <solana-tx> --chain solana --amount 10 --sender-signature <sig>
    python buy_key.py --tx 0xabc... --chain 8453 --amount 10 --app-name my-custom-name
"""
import argparse
import json
import sys
import urllib.request
import urllib.error

ENDPOINT = "https://api.insumermodel.com/v1/keys/buy"
DEFAULT_APP_NAME = "insumer-agent-skills"
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
    parser = argparse.ArgumentParser(description="Buy an InsumerAPI key with USDC.")
    parser.add_argument("--tx", required=True, help="Transaction hash proving payment")
    parser.add_argument("--chain", required=True,
                        help="Payment chain (USDC only): 1, 8453, 137, 42161, 10, 56, 43114 or 'solana'")
    parser.add_argument("--amount", type=float, required=True,
                        help="USDC amount sent (minimum 5)")
    parser.add_argument("--sender-signature",
                        help="Signature by the paying wallet over the text the API returns. "
                             "Omit it on the first run to get the exact text to sign.")
    parser.add_argument("--app-name", default=DEFAULT_APP_NAME,
                        help=f"App name (default: {DEFAULT_APP_NAME!r})")
    args = parser.parse_args()

    chain = int(args.chain) if args.chain.isdigit() else args.chain

    body_dict = {
        "txHash": args.tx,
        "chainId": chain,
        "amount": args.amount,
        "appName": args.app_name,
        "keyDelivery": "apiKey",
    }
    if args.sender_signature:
        body_dict["senderSignature"] = args.sender_signature

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
    key = data.get("key")
    if not key:
        print("Unexpected response:", json.dumps(payload, indent=2), file=sys.stderr)
        return 1

    print(f"\nKey purchased for {data.get('registeredWallet')}")
    print(f"  Tier:           {data.get('tier')}")
    print(f"  Daily limit:    {data.get('dailyLimit')}")
    print(f"  Credits added:  {data.get('creditsAdded')}")
    print(f"  Total credits:  {data.get('totalCredits')}")
    print(f"  Paid:           ${data.get('usdcPaid')} USDC ({data.get('chainName')})")
    print(f"  Effective rate: {data.get('effectiveRate')}")
    print(f"\nStore this key securely (shown only once):\n")
    print(f"    export INSUMER_API_KEY='{key}'\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
