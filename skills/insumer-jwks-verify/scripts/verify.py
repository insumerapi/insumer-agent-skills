#!/usr/bin/env python3
"""
Verify an InsumerAPI signed response offline against the public JWKS.

Accepts either:
- A bare JWT string on stdin (when format: "jwt" was requested)
- A full response JSON object on stdin (uses the .jwt field if present)

Usage:
    echo "eyJhbGc..." | python verify.py
    echo '{"jwt":"eyJhbGc...","kid":"insumer-attest-v2"}' | python verify.py

Requires:
    pip install pyjwt[crypto]
"""
import json
import sys

try:
    import jwt
    from jwt import PyJWKClient
except ImportError:
    print("Missing dependency. Install with:\n    pip install 'pyjwt[crypto]'", file=sys.stderr)
    sys.exit(1)

JWKS_URL = "https://insumermodel.com/.well-known/jwks.json"
ISSUER = "https://api.insumermodel.com"
ALGORITHMS = ["ES256"]


def extract_jwt(stdin_text: str):
    """Return the JWT to verify, or None when the input is a response object that carries no jwt."""
    stripped = stdin_text.strip()
    # Try parsing as JSON envelope first
    if stripped.startswith("{"):
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            return stripped
        # Look in common locations
        if isinstance(obj, dict):
            if isinstance(obj.get("jwt"), str):
                return obj["jwt"]
            if isinstance(obj.get("data"), dict) and isinstance(obj["data"].get("jwt"), str):
                return obj["data"]["jwt"]
        return None
    return stripped


def main() -> int:
    text = sys.stdin.read()
    if not text.strip():
        print("No input. Pipe a JWT or response JSON on stdin.", file=sys.stderr)
        return 1

    token = extract_jwt(text)
    if token is None:
        print("NOT CHECKED: the input is a response with no jwt field, so there is no JWT to verify. "
              "This is not a verdict on the response. A raw sig response (every trust profile, and "
              "attestations requested without format: \"jwt\") is verified with insumer-verify: "
              "pip install insumer-verify.", file=sys.stderr)
        return 1
    if not token or "." not in token:
        print("INVALID: input does not look like a JWT.", file=sys.stderr)
        return 1

    jwks_client = PyJWKClient(JWKS_URL)
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=ALGORITHMS,
            issuer=ISSUER,
        )
    except jwt.InvalidIssuerError as e:
        print(f"INVALID: issuer mismatch: {e}", file=sys.stderr)
        return 1
    except jwt.ExpiredSignatureError:
        print("INVALID: JWT has expired (past its exp: 30 min, or 5 for a delegation condition).", file=sys.stderr)
        return 1
    except jwt.InvalidSignatureError:
        print("INVALID: signature does not verify against the public JWKS.", file=sys.stderr)
        return 1
    except jwt.PyJWTError as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1

    print("OK")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
