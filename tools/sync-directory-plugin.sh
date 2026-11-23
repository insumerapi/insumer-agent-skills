#!/usr/bin/env bash
# Builds the skills the Claude directory plugin ships (plugins/insumerapi).
#
# The directory accepts only Markdown, text, JSON, YAML and images from an
# organization that is not Verified, and refuses a plugin that reads a key from
# the user's machine. So this plugin is the hosted MCP server plus two
# Markdown-only skills:
#   insumer-hosted-tools <- ../insumer-chatgpt-plugin/skills/ (its home; override
#                           with HOSTED_TOOLS_SRC=...)
#   insumer-jwks-verify  <- skills/ in this repo, without scripts/
# Lines that point at skills this plugin does not carry are rewritten below.
# Each rewrite must match exactly once, so a change at the source stops the sync.
#
#   tools/sync-directory-plugin.sh          rewrite the copy
#   tools/sync-directory-plugin.sh --check  exit 1 if the copy is stale
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
dest="$root/plugins/insumerapi/skills"
hosted_src="${HOSTED_TOOLS_SRC:-$root/../insumer-chatgpt-plugin/skills/insumer-hosted-tools}"

copy_dir() { # src dst [exclude-dir]
  mkdir -p "$2"
  (cd "$1" && find . -type f ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '.DS_Store' ${3:+! -path "./$3/*"} -print0 \
    | while IFS= read -r -d '' f; do mkdir -p "$2/$(dirname "$f")"; cp "$f" "$2/$f"; done)
}

build() {
  local out="$1"
  [[ -f "$hosted_src/SKILL.md" ]] || { echo "insumer-hosted-tools not found at $hosted_src" >&2; exit 1; }
  copy_dir "$hosted_src" "$out/insumer-hosted-tools"
  copy_dir "$root/skills/insumer-jwks-verify" "$out/insumer-jwks-verify" scripts
  python3 - "$out" <<'PY'
import re, sys
out = sys.argv[1]

def edit(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new, regex in pairs:
        if regex:
            s, n = re.subn(old, new, s, flags=re.S)
        else:
            n = s.count(old); s = s.replace(old, new)
        if n != 1:
            sys.exit(f"sync: expected one match in {path} for: {old[:60]!r} (found {n})")
    open(path, "w", encoding="utf-8").write(s)

DOCS = "https://insumermodel.com/developers/"

edit(f"{out}/insumer-hosted-tools/SKILL.md", [
    ("  transactions. Explains the shared daily allowance and when to switch to the\n  REST skills with the user's own key.\n",
     "  transactions. Explains the shared daily allowance and what to do when it\n  runs out.\n", False),
    ("Prefer them over the REST path in the other skills whenever they are available; the REST skills remain the reference for request shapes, response fields and verification.",
     f"The REST API reference, with full request and response shapes, is at {DOCS}", False),
    ("2. Offer the user's own free key: the `insumer-auth` skill creates one with an email address (10 verifications plus 100 requests a day, no card), and the `insumer-attest`, `insumer-trust` and `insumer-trust-batch` skills call the REST API with it.",
     f"2. Point the user to their own free key for the REST API ({DOCS}): it is created with an email address (10 verifications plus 100 requests a day, no card).", False),
    ("A key belongs in the user's own environment, as the REST skills describe.",
     "A key belongs in the user's own environment, never in the conversation.", False),
    (r"## Related skills\n.*\Z",
     "## Related skills\n\n- `insumer-jwks-verify`: verifying any signed response offline.\n", True),
])

edit(f"{out}/insumer-jwks-verify/SKILL.md", [
    (r"## Helper script\n.*?(?=## Error handling)", "", True),
    (r"## Related skills\n.*?(?=## References)",
     """## Related tools

This plugin connects the hosted InsumerAPI MCP server, which needs no account or key. Its tools produce the signed responses this skill verifies:

| Tool | Produces |
|---|---|
| `insumer_attest` | Signed attestation (`/v1/attest`) |
| `insumer_wallet_trust` | Signed wallet trust profile (`/v1/trust`) |
| `insumer_batch_wallet_trust` | One signed profile per wallet (`/v1/trust/batch`): verify each entry independently |
| `insumer_jwks` | The public signing keys |

""", True),
])
PY
}

scan() { # refuse anything key-shaped, a script, or any name on the private list
  # The names live outside the repository (INSUMER_LEAK_PATTERNS, default
  # ~/.insumer-leak-patterns, one extended regex per line). No file, no sync.
  local private="${INSUMER_LEAK_PATTERNS:-$HOME/.insumer-leak-patterns}"
  if [[ ! -s "$private" ]]; then
    echo "REFUSED: private leak patterns not found at $private" >&2; exit 1
  fi
  local pattern="insr_live_[0-9a-f]{12,}|BEGIN [A-Z ]*PRIVATE KEY|npm_[A-Za-z0-9]{30,}|$(grep -vE '^[[:space:]]*(#|$)' "$private" | paste -sd'|' -)"
  if grep -rEn "$pattern" "$root/plugins/insumerapi"; then
    echo "REFUSED: the lines above must not ship." >&2; exit 1
  fi
  local bad
  bad="$(find "$root/plugins/insumerapi" -type f ! -name '*.md' ! -name '*.json' ! -name '*.png' ! -name 'LICENSE')"
  if [[ -n "$bad" ]]; then
    echo "REFUSED: only Markdown, JSON, PNG and LICENSE may ship (directory rule for unverified publishers):" >&2
    echo "$bad" >&2; exit 1
  fi
  if grep -rln '^#!' "$root/plugins/insumerapi"; then
    echo "REFUSED: files starting with #! above" >&2; exit 1
  fi
}

if [[ "${1:-}" == "--check" ]]; then
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
  build "$tmp"
  if diff -r "$tmp" "$dest" >/dev/null; then scan; echo "directory plugin skills are current"; exit 0; fi
  echo "directory plugin skills are STALE: run tools/sync-directory-plugin.sh" >&2; exit 1
fi
rm -rf "$dest"; mkdir -p "$dest"
build "$dest"
scan
echo "synced: insumer-hosted-tools insumer-jwks-verify (Markdown only)"
