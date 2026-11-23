#!/usr/bin/env python3
"""
Build the EIP-4361 message that proves control of an EVM wallet for an
InsumerAPI discount, with a fresh nonce and the current time.

The wallet's owner signs it with personal_sign (EIP-191) within 5 minutes.
Send { "message": ..., "signature": ... } as "walletProof" on POST /v1/verify,
/v1/acp/discount or /v1/ucp/discount.

Example:
    python proof_message.py --merchant acme-store --wallet 0xd8dA...6045

This script never signs and never handles a private key: the wallet signs the
printed message itself.
"""
import argparse
import re
import secrets
import string
import sys
from datetime import datetime, timezone

DOMAIN = "api.insumermodel.com"


def build_message(merchant: str, wallet: str) -> str:
    alphabet = string.ascii_letters + string.digits
    nonce = "".join(secrets.choice(alphabet) for _ in range(16))
    now = datetime.now(timezone.utc)
    issued_at = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    return (
        f"{DOMAIN} wants you to sign in with your Ethereum account:\n"
        f"{wallet}\n"
        "\n"
        "Prove wallet for a discount.\n"
        "\n"
        f"URI: https://{DOMAIN}/v1/merchants/{merchant}\n"
        "Version: 1\n"
        "Chain ID: 1\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued_at}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the walletProof message for a wallet to sign")
    parser.add_argument("--merchant", required=True, help="Merchant ID, e.g. acme-store")
    parser.add_argument("--wallet", required=True, help="EVM wallet address (0x...)")
    args = parser.parse_args()

    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", args.wallet):
        print("--wallet must be an EVM address (0x + 40 hex characters).", file=sys.stderr)
        return 1
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.merchant):
        print("--merchant must be a merchant ID (letters, digits, - and _).", file=sys.stderr)
        return 1

    print(build_message(args.merchant, args.wallet))
    return 0


if __name__ == "__main__":
    sys.exit(main())
