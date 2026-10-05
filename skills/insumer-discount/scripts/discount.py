#!/usr/bin/env python3
"""
Token-holder discount at an InsumerAPI merchant.

By default: reads the store's terms (walletTerms) and runs the free discount
check for the wallet. Nothing is spent.

With --create: creates a signed single-use code with POST /v1/verify, which
uses one of the merchant's credits. Add --proof-file with the walletProof JSON
(from proof_message.py) for the proven route. Reads INSUMER_API_KEY from env.

Examples:
    python discount.py --merchant acme-store --wallet 0xd8dA...6045
    python discount.py --merchant acme-store --wallet 0xd8dA...6045 --create
    python discount.py --merchant acme-store --wallet 0xd8dA...6045 --create --proof-file proof.json
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.insumermodel.com/v1"


def call(method, url, body=None, api_key=None):
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(text)
        except json.JSONDecodeError:
            return e.code, {"ok": False, "error": {"message": text}}


def main() -> int:
    parser = argparse.ArgumentParser(description="Token-holder discount at an InsumerAPI merchant")
    parser.add_argument("--merchant", required=True, help="Merchant ID")
    parser.add_argument("--wallet", required=True, help="EVM wallet address (0x...)")
    parser.add_argument("--create", action="store_true", help="Create the code (uses a merchant credit)")
    parser.add_argument("--proof-file", help="walletProof JSON for the proven route")
    args = parser.parse_args()

    merchant = urllib.parse.quote(args.merchant, safe="")
    status, detail = call("GET", f"{API}/merchants/{merchant}")
    if status != 200:
        print(json.dumps(detail, indent=2))
        return 1
    terms = (detail.get("data") or {}).get("walletTerms")

    qs = urllib.parse.urlencode({"merchant": args.merchant, "wallet": args.wallet.lower()})
    status, check = call("GET", f"{API}/discount/check?{qs}")
    if status != 200:
        print(json.dumps(check, indent=2))
        return 1
    data = check.get("data") or {}
    summary = {
        "walletTerms": terms,
        "discountWithoutProof": data.get("totalDiscount"),
        "discountWithProof": data.get("discountIfProven", data.get("totalDiscount")),
    }

    if not args.create:
        print(json.dumps(summary, indent=2))
        return 0

    api_key = os.environ.get("INSUMER_API_KEY")
    if not api_key:
        print("INSUMER_API_KEY not set. See the insumer-auth skill.", file=sys.stderr)
        return 1
    body = {"merchantId": args.merchant, "wallet": args.wallet.lower()}
    if args.proof_file:
        with open(args.proof_file) as f:
            body["walletProof"] = json.load(f)
    status, result = call("POST", f"{API}/verify", body, api_key)
    print(json.dumps({"summary": summary, "status": status, "result": result}, indent=2))
    return 0 if status == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
