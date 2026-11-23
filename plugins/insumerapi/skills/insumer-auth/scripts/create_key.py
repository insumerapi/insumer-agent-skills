#!/usr/bin/env python3
"""
Create a free-tier InsumerAPI key.

Path 1 of 4 (see ../SKILL.md for the full decision matrix).
Prints the key and a `.env` snippet you can paste into your shell.

appName defaults to "insumer-agent-skills", a label on the key that tells
InsumerAPI which channel the key came from. Pass --app-name to use your own.

Usage:
    python create_key.py --email you@example.com
    python create_key.py --email you@example.com --app-name my-custom-name
"""
import argparse
import json
import sys
import urllib.request
import urllib.error

ENDPOINT = "https://api.insumermodel.com/v1/keys/create"
DEFAULT_APP_NAME = "insumer-agent-skills"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a free InsumerAPI key.")
    parser.add_argument("--email", required=True, help="Email address (one free key per email)")
    parser.add_argument("--app-name", default=DEFAULT_APP_NAME,
                        help=f"App name (default: {DEFAULT_APP_NAME!r})")
    args = parser.parse_args()

    body = json.dumps({
        "email": args.email,
        "appName": args.app_name,
        "tier": "free",
    }).encode("utf-8")

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

    key = payload.get("key")
    if not key:
        print("Unexpected response:", json.dumps(payload, indent=2), file=sys.stderr)
        return 1

    print(f"\nFree key created for {args.email}")
    print(f"  Tier:        {payload.get('tier')}")
    print(f"  Daily limit: {payload.get('dailyLimit')} requests/day")
    print(f"  Credits:     {payload.get('apiKeyCredits')}")
    print(f"\nAdd this to your shell profile (~/.zshrc, ~/.bashrc) or .env:\n")
    print(f"    export INSUMER_API_KEY='{key}'\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
