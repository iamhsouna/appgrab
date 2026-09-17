# AppGrab

> One friendly CLI to search and bulk-download **Android APKs** (Google Play / APKPure / F-Droid / Huawei) and **iOS IPAs** (Apple App Store).

AppGrab wraps [`apkeep`](https://github.com/EFForg/apkeep) and [`ipatool`](https://github.com/majd/ipatool) behind a single, self-bootstrapping Python script. Point it at a search term and it grabs everything for you.

```
$ ./appgrab.py search "dubai rest" -p ios
→ Searching the App Store for "dubai rest" (limit=10) ...

   1. ae.gov.dubailand.selfregistration               Dubai REST (v7.2.1)
   2. com.deg.mdubai                                  DubaiNow (v14.6.30)
   3. com.bayut.bayutapp                              Bayut – UAE Property Search (v16.1.4)
   ...

Download all 10 apps to '.'? [y/N] y
→ Downloading 10 apps from the App Store (parallel=4) ...
✓ All downloads complete. Files in: /Users/you/apps
```

## Features

- **Two platforms, one tool** — Android (`.apk`) and iOS (`.ipa`) with a single `-p android|ios` switch.
- **Search or direct download** — search a store and bulk-grab every result, or download a single app by id.
- **Automatic fallback** — if the Google Play / APKPure source can't provide an app (missing there, geo-restricted, or no credentials), AppGrab retries it from Huawei AppGallery.
- **Cross-platform** — works on **macOS**, **Ubuntu/Debian**, **Arch Linux** (and other `brew` / `apt` / `pacman` / `dnf` / `zypper` distros).
- **Zero setup** — missing dependencies are detected and installed on first run *with your permission*.
- **`uv` or `venv`** — uses [PEP 723](https://peps.python.org/pep-0723/) inline metadata with `uv`, and falls back to a private virtualenv if `uv` isn't installed.
- **No auth for free sources** — Android defaults to APKPure; iOS only needs your own App Store account login.
- **Pretty output** — colored, script-friendly progress, and `Ctrl+C` exits cleanly without a traceback.

## Requirements

- Python 3.9+
- [`uv`](https://docs.astral.sh/uv/) *(recommended, optional — otherwise a venv is created)*

Everything else is installed on demand. AppGrab always asks before installing
anything, and picks a strategy that works on your OS:

| Dependency | Needed for | How AppGrab installs it |
| --- | --- | --- |
| `google-play-scraper` | Android search | isolated `uv` env, else a private venv |
| [`apkeep`](https://github.com/EFForg/apkeep) | Android downloads | prebuilt binary (Linux), Homebrew, or `cargo install apkeep` |
| [`ipatool`](https://github.com/majd/ipatool) | iOS | prebuilt binary (macOS/Linux), Homebrew, or `go install` |
| Rust/cargo | only if building `apkeep` | `brew` / `apt` / `pacman` / `dnf`, else rustup |
| Go | only if building `ipatool` | `brew` / `apt` / `pacman` / `dnf` |

Prebuilt binaries are downloaded straight from the official GitHub releases
(with SHA-256 verification when the project publishes one), so most users never
need a compiler.

### Supported platforms

- **macOS** (Intel & Apple Silicon)
- **Ubuntu / Debian** (and derivatives)
- **Arch Linux** (and derivatives)
- Other Linux with `dnf`/`zypper`/Homebrew

Pass `-y` / `--yes` (or set `APPGRAB_YES=1`) to auto-accept every prompt — handy
for unattended installs and CI.

## Install

### One-line installer (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/iamhsouna/appgrab/main/install.sh | bash
```

Then run `appgrab --help`. The installer prefers an isolated [`uv`](https://docs.astral.sh/uv/)
tool install, falls back to `pipx`, then to dropping the single script in
`~/.local/bin`.

> **Private repo?** `raw.githubusercontent.com` needs a token. Use the `uv` one-liner
> below instead (Git uses your stored credentials), or run
> `gh api repos/iamhsouna/appgrab/contents/install.sh -H "Accept: application/vnd.github.raw" | bash`.

### `uv` one-liner

```bash
uv tool install "git+https://github.com/iamhsouna/appgrab"
```

### Manual / from a clone

```bash
git clone https://github.com/iamhsouna/appgrab.git
cd appgrab
./install.sh          # or: ./appgrab.py --help
```

Run it without installing anything (uses `uv` for an ephemeral env):

```bash
uv run appgrab.py --help
```

## Usage

```
appgrab <command> [options]

Commands:
  setup      Configure credentials (Google Play AAS token or App Store login)
  search     Search a store and download all results
  download   Download a single app by bundle/app id
  update     Update AppGrab to the latest version
```

Common options:

| Flag | Description |
| --- | --- |
| `-p, --platform {android,ios}` | Target platform (default: `android`) |
| `-o, --output DIR` | Output directory (default: `.`) |
| `-r, --parallel N` | Parallel downloads (default: `4`) |
| `--limit N` | Max search results (default: `10`) |
| `-y, --yes` | Auto-accept install/download prompts (`APPGRAB_YES=1` also works) |
| `--dry-run` | List results without downloading |
| `-s, --source` | Android source: `apk-pure`, `google-play`, `f-droid`, `huawei-app-gallery` |
| `--fallback / --no-fallback` | Android: fall back to Huawei AppGallery when the chosen source can't provide an app (default: on) |
| `--purchase / --no-purchase` | iOS: acquire a license if required (default: on) |

### Android

```bash
# Search Google Play and download every result from the free APKPure source
./appgrab.py search "whatsapp"

# Only list results
./appgrab.py search "whatsapp" --dry-run

# Download a single app
./appgrab.py download com.whatsapp -o ./apks

# Use a different source
./appgrab.py search "fdroid" -s f-droid
```

**Google Play source** needs a Google email + AAS token:

```bash
./appgrab.py setup            # prompts for email + AAS token
./appgrab.py download com.whatsapp -s google-play
```

**Huawei AppGallery fallback** is on by default for the `apk-pure` and
`google-play` sources: any app they can't provide is automatically retried from
Huawei AppGallery (useful for region-specific apps). Disable it with
`--no-fallback`:

```bash
./appgrab.py search "whatsapp" -s google-play --no-fallback
```

### iOS

```bash
# One-time App Store sign-in (wraps `ipatool auth login`)
./appgrab.py setup -p ios

# Search the App Store
./appgrab.py search "dubai rest" -p ios

# Download a single app by bundle id (or numeric app id)
./appgrab.py download ae.gov.dubailand.selfregistration -p ios -o ./ipas
```

Downloads are saved as `{bundleID}_{appID}_{version}.ipa`.

## Updating

Update in place — no need to re-run the installer:

```bash
appgrab update           # update to the latest version
appgrab update --check   # just report whether an update is available
appgrab --version        # show the installed version
```

`appgrab update` detects how it was installed and does the right thing:

| Installation | What `update` runs |
| --- | --- |
| git clone | `git pull --ff-only` |
| `uv tool install` | `uv tool upgrade appgrab` (falls back to reinstall) |
| `pipx install` | `pipx install --force git+…` |
| single-file in `~/.local/bin` | re-downloads the latest `appgrab.py` |

> For a **private** repo, updating needs GitHub auth: have `gh auth login` done,
> or set `GITHUB_TOKEN`.

## How it works

1. `appgrab.py` carries inline [PEP 723](https://peps.python.org/pep-0723/) metadata listing its Python dependency.
2. On first Android search, if `google-play-scraper` is missing the script asks,
   then re-executes itself under `uv run` (preferred) or a private venv at
   `~/.cache/appgrab/venv`.
3. Missing native tools are detected by OS/architecture. AppGrab asks before
   installing anything, then tries, in order: a prebuilt GitHub release binary →
   the system package manager (`brew` / `apt` / `pacman` / `dnf` / `zypper`) →
   building from source with `cargo` / `go` (installing that toolchain too, if you agree).
4. Installed binaries land in `~/.local/bin` (or `~/.cargo/bin` / `~/go/bin`),
   which AppGrab adds to `PATH` for the current session.
5. Search + download is delegated to the native tool, with JSON output parsed by AppGrab.

Config for the Google Play source is stored at `~/.config/appgrab/config.json` (mode `0600`).

## Disclaimer

Download only apps you have the right to download, and respect the terms of service of Google Play, the Apple App Store, and the upstream tools. Use at your own risk.

## License

[MIT](LICENSE)
