#!/usr/bin/env bash
# AppGrab installer.
#
#   Local clone:   ./install.sh
#   One-liner:     curl -fsSL https://raw.githubusercontent.com/iamhsouna/appgrab/main/install.sh | bash
#
# Prefers `uv tool` (or pipx) for an isolated install, and falls back to
# dropping the single self-bootstrapping appgrab.py into ~/.local/bin.

set -euo pipefail

REPO="${APPGRAB_REPO:-iamhsouna/appgrab}"
REF="${APPGRAB_REF:-main}"
BIN_DIR="${APPGRAB_BIN:-$HOME/.local/bin}"

say() { printf '\033[36m→ %s\033[0m\n' "$1"; }
ok()  { printf '\033[32m✓ %s\033[0m\n' "$1"; }
die() { printf '\033[31m✗ %s\033[0m\n' "$1" >&2; exit 1; }

# Directory of this script, if we're running from a checkout.
SELF_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

# 1) uv (recommended): isolated tool install, deps handled automatically.
if command -v uv >/dev/null 2>&1; then
    if [ -n "$SELF_DIR" ] && [ -f "$SELF_DIR/appgrab.py" ]; then
        say "Installing AppGrab with uv (local checkout) ..."
        uv tool install --force "$SELF_DIR"
    else
        say "Installing AppGrab with uv ..."
        uv tool install --force "git+https://github.com/${REPO}.git@${REF}"
    fi
    ok "Installed. Run: appgrab --help"
    exit 0
fi

# 2) pipx: same idea, no uv required.
if command -v pipx >/dev/null 2>&1; then
    if [ -n "$SELF_DIR" ] && [ -f "$SELF_DIR/pyproject.toml" ]; then
        say "Installing AppGrab with pipx (local checkout) ..."
        pipx install --force "$SELF_DIR"
    else
        say "Installing AppGrab with pipx ..."
        pipx install --force "git+https://github.com/${REPO}.git@${REF}"
    fi
    ok "Installed. Run: appgrab --help"
    exit 0
fi

# 3) Fallback: grab the single self-contained script.
say "uv/pipx not found - downloading appgrab.py ..."
mkdir -p "$BIN_DIR"

if [ -n "$SELF_DIR" ] && [ -f "$SELF_DIR/appgrab.py" ]; then
    cp "$SELF_DIR/appgrab.py" "$BIN_DIR/appgrab"
elif command -v gh >/dev/null 2>&1; then
    gh api "repos/${REPO}/contents/appgrab.py?ref=${REF}" \
        -H "Accept: application/vnd.github.raw" > "$BIN_DIR/appgrab" \
        || die "download failed. Try: gh auth login"
elif [ -n "${GITHUB_TOKEN:-}" ]; then
    curl -fsSL -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        "https://api.github.com/repos/${REPO}/contents/appgrab.py?ref=${REF}" \
        -H "Accept: application/vnd.github.raw" > "$BIN_DIR/appgrab" \
        || die "download failed."
else
    curl -fsSL "https://raw.githubusercontent.com/${REPO}/${REF}/appgrab.py" \
        -o "$BIN_DIR/appgrab" \
        || die "download failed (private repo? set GITHUB_TOKEN or run 'gh auth login')."
fi

chmod +x "$BIN_DIR/appgrab"
ok "Installed to $BIN_DIR/appgrab"

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) printf '\033[33m! Add to your PATH: export PATH="%s:$PATH"\033[0m\n' "$BIN_DIR" ;;
esac
ok "Run: appgrab --help"
