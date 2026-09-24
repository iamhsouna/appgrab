#!/usr/bin/env bash
# AppGrab installer.
#
#   Local clone:   ./install.sh
#   One-liner:     curl -fsSL https://raw.githubusercontent.com/iamhsouna/appgrab/main/install.sh | bash
#
# Prefers `uv tool` (or pipx) for an isolated install, and falls back to
# dropping the single self-bootstrapping appgrab.py into ~/.local/bin.
# The install directory is added to PATH (set APPGRAB_NO_MODIFY_PATH=1 to skip),
# and all runtime dependencies (apkeep, ipatool, Python env) are installed
# (set APPGRAB_SKIP_DEPS=1 to skip).

set -euo pipefail

REPO="${APPGRAB_REPO:-iamhsouna/appgrab}"
REF="${APPGRAB_REF:-main}"
BIN_DIR="${APPGRAB_BIN:-$HOME/.local/bin}"
NO_MODIFY_PATH="${APPGRAB_NO_MODIFY_PATH:-}"
PATH_MARKER="# Added by AppGrab installer"

say() { printf '\033[36m→ %s\033[0m\n' "$1"; }
ok()  { printf '\033[32m✓ %s\033[0m\n' "$1"; }
die() { printf '\033[31m✗ %s\033[0m\n' "$1" >&2; exit 1; }

# ---------- PATH handling ----------
path_contains() {
    case ":$PATH:" in
        *":$1:"*) return 0 ;;
        *) return 1 ;;
    esac
}

shell_profile() {
    # Pick the startup file the user's login shell actually reads.
    case "$(basename "${SHELL:-sh}")" in
        zsh)
            if [ -f "$HOME/.zshrc" ]; then printf '%s\n' "$HOME/.zshrc"
            elif [ -f "$HOME/.zprofile" ]; then printf '%s\n' "$HOME/.zprofile"
            else printf '%s\n' "$HOME/.zshenv"; fi
            ;;
        bash)
            if [ -f "$HOME/.bashrc" ]; then printf '%s\n' "$HOME/.bashrc"
            elif [ -f "$HOME/.bash_profile" ]; then printf '%s\n' "$HOME/.bash_profile"
            else printf '%s\n' "$HOME/.profile"; fi
            ;;
        *) printf '%s\n' "$HOME/.profile" ;;
    esac
}

persist_path() {
    # Append an export line to the user's shell profile, idempotently.
    local dir="$1" file line
    if path_contains "$dir"; then
        return 0
    fi
    if [ -n "$NO_MODIFY_PATH" ]; then
        printf '\033[33m! Add to your PATH: export PATH="%s:$PATH"\033[0m\n' "$dir"
        return 0
    fi
    file="$(shell_profile)"
    if [ -f "$file" ] && grep -qF "$dir" "$file"; then
        say "$dir is already referenced in $file"
        return 0
    fi
    line="export PATH=\"$dir:\$PATH\""
    if printf '\n%s\n%s\n' "$PATH_MARKER" "$line" >> "$file"; then
        say "Added $dir to PATH in $file"
    else
        printf '\033[33m! Could not update %s. Add to your PATH: %s\033[0m\n' "$file" "$line"
    fi
}

find_appgrab() {
    # Locate the just-installed command, even if PATH isn't refreshed yet.
    local candidate
    if command -v appgrab >/dev/null 2>&1; then
        printf '%s\n' "appgrab"
        return 0
    fi
    for candidate in "$BIN_DIR/appgrab"; do
        if [ -x "$candidate" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    if command -v uv >/dev/null 2>&1; then
        local uv_bin
        uv_bin="$(uv tool dir --bin 2>/dev/null || true)"
        if [ -n "$uv_bin" ] && [ -x "$uv_bin/appgrab" ]; then
            printf '%s\n' "$uv_bin/appgrab"
            return 0
        fi
    fi
    return 1
}

install_deps() {
    # Install every runtime dependency (Python env, apkeep, ipatool).
    if [ -n "${APPGRAB_SKIP_DEPS:-}" ]; then
        say "Skipping dependency installation (APPGRAB_SKIP_DEPS set)."
        return 0
    fi
    local cmd
    if ! cmd="$(find_appgrab)"; then
        warn "Could not locate the installed appgrab command; skipping dependencies."
        return 0
    fi
    say "Installing runtime dependencies (Python env, apkeep, ipatool) ..."
    if "$cmd" install-deps -y; then
        ok "All dependencies installed."
    else
        warn "Dependency installation did not finish. Retry with: $cmd install-deps"
        warn "AppGrab will also retry automatically on first use."
    fi
}

finish() {
    install_deps
    # Make sure the install location (and uv's bin dir) are on PATH, now and later.
    persist_path "$BIN_DIR"
    if command -v uv >/dev/null 2>&1; then
        local uv_bin
        uv_bin="$(uv tool dir --bin 2>/dev/null || true)"
        if [ -n "$uv_bin" ] && [ "$uv_bin" != "$BIN_DIR" ]; then
            persist_path "$uv_bin"
        fi
    fi
    if path_contains "$BIN_DIR"; then
        ok "Run: appgrab --help"
    else
        ok "Run: appgrab --help"
        say "Open a new terminal (or 'source $(shell_profile)') to refresh your PATH."
    fi
}

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
    finish
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
    finish
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

finish
