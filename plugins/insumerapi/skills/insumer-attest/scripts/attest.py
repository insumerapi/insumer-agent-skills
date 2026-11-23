#!/usr/bin/env python3
"""
Call POST /v1/attest with a JSON conditions payload.

Reads INSUMER_API_KEY from env. Accepts the request body on stdin or via
--body-file. Prints the signed response to stdout.

Examples:
    # From stdin:
    cat request.json | python attest.py

    # From file:
    python attest.py --body-file request.json

Request body shape (see ../SKILL.md and ../references/condition-shapes.md):
    {
      "wallet": "0x...",
      "conditions": [{ "type": "token_balance", ... }]
    }

Optional fields: format ("jwt"), proof ("merkle"),
solanaWallet, xrplWallet, bitcoinWallet, tronWallet, stellarWallet, suiWallet.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

ENDPOINT = "https://api.insumermodel.com/v1/attest"


def main() -> int:
    parser = argparse.ArgumentParser(description="POST /v1/attest")
    parser.add_argument("--body-file", help="Read JSON request body from file (otherwise stdin)")
    args = parser.parse_args()

    api_key = os.environ.get("INSUMER_API_KEY")
    if not api_key:
        print("INSUMER_API_KEY not set. See the insumer-auth skill.", file=sys.stderr)
        return 1

    if args.body_file:
        with open(args.body_file) as f:
            body_text = f.read()
    else:
        body_text = sys.stdin.read()

    try:
        body_obj = json.loads(body_text)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        return 1

    body = json.dumps(body_obj).encode("utf-8")

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
