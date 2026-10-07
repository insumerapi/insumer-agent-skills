#!/usr/bin/env python3
"""
Call POST /v1/trust/batch for multiple wallets in one request (max 10).

Reads INSUMER_API_KEY from env. Each successful wallet costs 3 credits (or 6
with merkle). Builds the proper array-of-objects request body.

Usage:
    python trust_batch.py --wallets 0xabc...,0xdef...
    python trust_batch.py --wallets-file allowlist.txt
    python trust_batch.py --wallets-file allowlist.txt --proof merkle
    python trust_batch.py --wallets 0xabc... --full

Output:
    By default the script prints a short summary per wallet (profile ID, held /
    not held / not evaluated counts, and the checks held in each dimension) and
    writes the complete signed response to a JSON file, named in the summary.
    Dimensions print in a fixed order (the base dimensions stablecoins through
    names, then account, then solana, xrpl, bitcoin, tron where present); the
    account dimension's checks read "present" rather than "held".
    A full profile is tens of thousands of characters, so ten of them are more
    than an agent can read at once; the file keeps every signed profile intact
    for verification. --out PATH chooses the file. --full prints the complete
    response instead of the summary.

Wallet input formats:
    - --wallets: comma-separated EVM addresses (no per-wallet cross-chain fields)
    - --wallets-file: one EVM address per line, OR one JSON object per line for
      per-wallet cross-chain fields, e.g.:
          {"wallet":"0x...","solanaWallet":"5v9..."}
          {"wallet":"0x...","xrplWallet":"rN7n..."}
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

ENDPOINT = "https://api.insumermodel.com/v1/trust/batch"
MAX_WALLETS = 10

# The order the dimensions print in, the same for every wallet: the base
# dimensions first, then the optional wallet dimensions, then anything else
# alphabetically.
BASE_DIMENSIONS = (
    "stablecoins", "governance", "nfts", "staking", "institutional_stablecoins",
    "tokenized_treasuries", "stablecoin_deposits", "wrapped_bitcoin", "names", "account",
)
OPTIONAL_DIMENSIONS = ("solana", "xrpl", "bitcoin", "tron")
# Dimensions whose checks are states at the wallet address rather than holdings.
PRESENCE_DIMENSIONS = ("account",)


def _ordered_dimensions(dims: dict) -> list:
    """Return the dimension names of a profile in the fixed print order."""
    fixed = [n for n in BASE_DIMENSIONS + OPTIONAL_DIMENSIONS if n in dims]
    return fixed + sorted(n for n in dims if n not in fixed)


def _s(value) -> str:
    return "" if value is None else str(value)


def _int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _signed(entry: dict) -> bool:
    sig, kid = entry.get("sig"), entry.get("kid")
    return isinstance(entry.get("trust"), dict) and isinstance(sig, str) and bool(sig) and isinstance(kid, str) and bool(kid)


def summarize(payload: dict, saved_to: str):
    """Return a short summary, or None when the response carries no results list."""
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    results = data.get("results")
    if not isinstance(results, list):
        return None
    counts = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    signed = sum(1 for e in results if isinstance(e, dict) and _signed(e))
    requested = _int(counts.get("requested"))
    succeeded = _int(counts.get("succeeded"))
    failed = _int(counts.get("failed"))
    out = [
        f"Batch trust profiles: {len(results) if requested is None else requested} requested, "
        f"{signed if succeeded is None else succeeded} signed, "
        f"{len(results) - signed if failed is None else failed} not signed. "
        f"Credits charged: {_s(meta.get('creditsCharged'))}.",
        f"This is a summary. The complete signed response (each profile with sig, kid, pqSig and pqKid, unchanged) "
        f"is saved in {saved_to}. Verify each entry of data.results there against the InsumerAPI JWKS on the raw "
        f"sig path, for example with verify_trust_profile from the insumer-verify package. "
        f"Profiles cannot be fetched again: a new call signs fresh profiles and is charged again.",
        "Every check is held or not held (present or not present for the account dimension), never a balance. "
        "The counts are facts about the wallet, not a score.",
        "",
    ]
    for i, entry in enumerate(results, start=1):
        e = entry if isinstance(entry, dict) else {}
        trust = e.get("trust")
        if isinstance(trust, dict):
            s = trust.get("summary") if isinstance(trust.get("summary"), dict) else {}
            if _signed(e):
                pq = f" + {e['pqKid']}" if e.get("pqKid") and e.get("pqSig") else ""
                signature = f"signed ({e['kid']}{pq})"
            else:
                signature = "returned without a signature: do not rely on it"
            out.append(f"{i}. {_s(trust.get('wallet'))} · {_s(trust.get('id'))} · check set "
                       f"{_s(trust.get('conditionSetVersion'))} · expires {_s(trust.get('expiresAt'))} · {signature}")
            out.append(f"   {_s(s.get('totalChecks'))} checks: {_s(s.get('totalPassed'))} held, "
                       f"{_s(s.get('totalFailed'))} not held, {_s(s.get('totalNotEvaluated'))} not evaluated")
            dims = trust.get("dimensions") if isinstance(trust.get("dimensions"), dict) else {}
            for name in _ordered_dimensions(dims):
                dim = dims[name]
                if not isinstance(dim, dict):
                    continue
                checks = [c for c in dim.get("checks") if isinstance(c, dict)] if isinstance(dim.get("checks"), list) else []
                held = [_s(c.get("label")) for c in checks if c.get("met") is True]
                not_eval = sum(1 for c in checks if c.get("evaluated") is False)
                total = _int(dim.get("total"))
                word = "present" if name in PRESENCE_DIMENSIONS else "held"
                line = f"   {name}: {len(held)} of {len(checks) if total is None else total} {word}"
                if not_eval:
                    line += f" ({not_eval} not evaluated)"
                if held:
                    line += ": " + ", ".join(held)
                out.append(line)
        else:
            raw = e.get("error")
            err = raw if isinstance(raw, dict) else {}
            reason = _s(err.get("message")) or _s(err.get("code")) or (raw if isinstance(raw, str) else "no reason given")
            out.append(f"{i}. {_s(err.get('wallet')) or '(wallet not named)'} · not signed: {reason}")
            out.append("   No profile was signed for this wallet and no credits were charged for it. "
                       "Retry this wallet; never read this entry as a no.")
        out.append("")
    return "\n".join(out).rstrip()


def save_response(raw: bytes, path: str):
    """Write the response without overwriting anything. Returns the absolute path, or None if it could not be written."""
    base = path
    for attempt in range(5):
        candidate = base if attempt == 0 else f"{base}.{os.getpid()}.{attempt}"
        try:
            with open(candidate, "xb") as f:
                f.write(raw)
            return os.path.abspath(candidate)
        except FileExistsError:
            continue
        except OSError as e:
            print(f"Could not save the response to {candidate}: {e}", file=sys.stderr)
            return None
    print(f"Could not save the response: {base} and its alternatives already exist.", file=sys.stderr)
    return None


def parse_wallets_file(path: str) -> list:
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("{"):
                # JSON-line format with cross-chain fields
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON line: {line!r} — {e}", file=sys.stderr)
                    sys.exit(1)
                if "wallet" not in obj:
                    print(f"Missing 'wallet' in line: {line!r}", file=sys.stderr)
                    sys.exit(1)
                entries.append(obj)
            else:
                entries.append({"wallet": line})
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="POST /v1/trust/batch")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--wallets", help="Comma-separated EVM addresses")
    group.add_argument("--wallets-file", help="Path to file (one address or JSON obj per line)")
    parser.add_argument("--proof", choices=["merkle"],
                        help="Set 'merkle' for EIP-1186 proofs (6 credits/wallet)")
    parser.add_argument("--full", action="store_true",
                        help="Print the complete signed response instead of the summary")
    parser.add_argument("--out",
                        help="Where to save the complete signed response (default: trust_batch_<time>.json); "
                             "an existing file is never overwritten")
    args = parser.parse_args()

    api_key = os.environ.get("INSUMER_API_KEY")
    if not api_key:
        print("INSUMER_API_KEY not set. See the insumer-auth skill.", file=sys.stderr)
        return 1

    if args.wallets:
        entries = [{"wallet": w.strip()} for w in args.wallets.split(",") if w.strip()]
    else:
        entries = parse_wallets_file(args.wallets_file)

    if not entries:
        print("No wallets provided.", file=sys.stderr)
        return 1

    if len(entries) > MAX_WALLETS:
        print(f"Too many wallets ({len(entries)}). Max per call is {MAX_WALLETS}. "
              f"Batch client-side and call multiple times.", file=sys.stderr)
        return 1

    body_dict = {"wallets": entries}
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
            raw = resp.read()
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {err_body}", file=sys.stderr)
        return 1

    if args.full:
        try:
            print(json.dumps(json.loads(raw.decode("utf-8")), indent=2))
        except ValueError:
            sys.stdout.write(raw.decode("utf-8", errors="replace"))
        return 0

    # The call has been paid for: whatever happens below, the response is either
    # saved or printed in full, never lost. It is saved before it is parsed.
    saved = save_response(raw, args.out or f"trust_batch_{time.strftime('%Y%m%dT%H%M%S')}.json")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except ValueError:
        print("The response was not JSON." + (f" It is saved in {saved}." if saved else ""), file=sys.stderr)
        sys.stdout.write(raw.decode("utf-8", errors="replace"))
        return 1
    summary = summarize(payload, saved) if saved else None
    if summary is None:
        print(f"The complete response is saved in {saved}." if saved else "Printing the complete response instead.", file=sys.stderr)
        print(json.dumps(payload, indent=2))
        return 0
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
