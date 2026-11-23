#!/usr/bin/env python3
"""
Call POST /v1/trust for a single wallet.

Reads INSUMER_API_KEY from env. Returns the curated multi-dimensional profile.

Usage:
    python trust.py --wallet 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
    python trust.py --wallet 0x... --solana 5xY... --xrpl rN7n... --bitcoin bc1q...
    python trust.py --wallet 0x... --tron T... --stellar G... --sui 0x...
    python trust.py --wallet 0x... --proof merkle
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

ENDPOINT = "https://api.insumermodel.com/v1/trust"


def main() -> int:
    parser = argparse.ArgumentParser(description="POST /v1/trust")
    parser.add_argument("--wallet", required=True, help="EVM wallet (0x... 40 hex chars)")
    parser.add_argument("--solana", help="Optional Solana wallet (base58)")
    parser.add_argument("--xrpl", help="Optional XRPL wallet (r-address)")
    parser.add_argument("--bitcoin", help="Optional Bitcoin address")
    parser.add_argument("--tron", help="Optional Tron wallet (T-address)")
    parser.add_argument("--stellar", help="Optional Stellar wallet (G-address; adds no dimension, evaluates the Stellar rows in institutional stablecoins)")
    parser.add_argument("--sui", help="Optional Sui wallet (0x + 64 hex chars; adds no dimension, evaluates the Sui rows: institutional USDC and tokenized-treasury USDY)")
    parser.add_argument("--proof", choices=["merkle"], help="Set 'merkle' for EIP-1186 proofs (6 credits)")
    args = parser.parse_args()

    api_key = os.environ.get("INSUMER_API_KEY")
    if not api_key:
        print("INSUMER_API_KEY not set. See the insumer-auth skill.", file=sys.stderr)
        return 1

    body_dict = {"wallet": args.wallet}
    if args.solana:
        body_dict["solanaWallet"] = args.solana
    if args.xrpl:
        body_dict["xrplWallet"] = args.xrpl
    if args.bitcoin:
        body_dict["bitcoinWallet"] = args.bitcoin
    if args.tron:
        body_dict["tronWallet"] = args.tron
    if args.stellar:
        body_dict["stellarWallet"] = args.stellar
    if args.sui:
        body_dict["suiWallet"] = args.sui
    if args.proof:
        body_dict["proof"] = args.proof

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
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {err_body}", file=sys.stderr)
        return 1

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
