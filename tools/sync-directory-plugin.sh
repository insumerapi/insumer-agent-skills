#!/usr/bin/env bash
# Copies the skills the Claude directory plugin ships (plugins/insumerapi).
# Same set as the ChatGPT plugin, minus insumer-x402-recipes (it calls services
# InsumerAPI does not run, which the Claude directory does not allow).
#
#   six REST skills     <- skills/ in this repo (edit them there, never in the copy)
#   insumer-hosted-tools <- ../insumer-chatgpt-plugin/skills/ (its home; override
#                           with HOSTED_TOOLS_SRC=...)
#
#   tools/sync-directory-plugin.sh          rewrite the copy
#   tools/sync-directory-plugin.sh --check  exit 1 if the copy is stale
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
dest="$root/plugins/insumerapi/skills"
hosted_src="${HOSTED_TOOLS_SRC:-$root/../insumer-chatgpt-plugin/skills/insumer-hosted-tools}"
rest=(insumer-auth insumer-attest insumer-trust insumer-trust-batch insumer-jwks-verify insumer-discount)

copy_dir() { # src dst
  mkdir -p "$2"
  (cd "$1" && find . -type f ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '.DS_Store' -print0 \
    | while IFS= read -r -d '' f; do mkdir -p "$2/$(dirname "$f")"; cp "$f" "$2/$f"; done)
}

build() {
  local out="$1"
  for s in "${rest[@]}"; do copy_dir "$root/skills/$s" "$out/$s"; done
  [[ -f "$hosted_src/SKILL.md" ]] || { echo "insumer-hosted-tools not found at $hosted_src" >&2; exit 1; }
  copy_dir "$hosted_src" "$out/insumer-hosted-tools"
}

scan() { # refuse anything key-shaped, or any name on the private list, same rule as the ChatGPT build
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
echo "synced: ${rest[*]} insumer-hosted-tools"
