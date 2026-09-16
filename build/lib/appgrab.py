#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["google-play-scraper"]
# ///
"""
AppGrab - search and bulk-download Android APKs (apkeep) and iOS IPAs (ipatool)
from one friendly CLI. Dependencies are resolved automatically (uv preferred,
a private venv as fallback); Android defaults to the free APKPure source.

    ./appgrab.py search "dubai rest" -p ios
    ./appgrab.py search "whatsapp" -p android
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "appgrab"
CONFIG_FILE = CONFIG_DIR / "config.json"

SCRIPT_PATH = Path(__file__).resolve()
BOOTSTRAP_ENV = "_APPGRAB_BOOTSTRAPPED"
VENV_DIR = Path(os.environ.get("APPGRAB_VENV", Path.home() / ".cache" / "appgrab" / "venv"))


# ---------- Colors ----------
def c(text, code): return f"\033[{code}m{text}\033[0m"
def ok(msg):    print(c(f"✓ {msg}", "32"), flush=True)
def info(msg):  print(c(f"→ {msg}", "36"), flush=True)
def warn(msg):  print(c(f"! {msg}", "33"), file=sys.stderr, flush=True)
def err(msg):   print(c(f"✗ {msg}", "31"), file=sys.stderr, flush=True)


# ---------- Dependency installer ----------
def run(cmd, **kwargs):
    """Run a command and return True on success."""
    try:
        subprocess.run(cmd, check=True, **kwargs)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def have_google_play_scraper():
    try:
        import google_play_scraper  # noqa: F401
        return True
    except ImportError:
        return False


def bootstrap_python_env():
    """Make sure google-play-scraper is importable.

    Prefers `uv` (which understands the PEP 723 metadata at the top of this
    file), and falls back to creating a private virtualenv. The process is
    re-executed inside the resolved environment.
    """
    if have_google_play_scraper():
        return

    if os.environ.get(BOOTSTRAP_ENV) == "1":
        err("google-play-scraper is still unavailable after bootstrapping.")
        sys.exit(1)
    os.environ[BOOTSTRAP_ENV] = "1"

    def reexec(program, argv):
        sys.stdout.flush()
        sys.stderr.flush()
        os.execv(program, argv)

    uv = shutil.which("uv")
    if uv:
        info("Setting up isolated environment with uv ...")
        reexec(uv, [uv, "run", "--quiet", str(SCRIPT_PATH), *sys.argv[1:]])

    info("uv not found - creating a private virtualenv ...")
    venv_py = VENV_DIR / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
    if not venv_py.exists():
        VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
        if not run([sys.executable, "-m", "venv", str(VENV_DIR)]):
            err("Failed to create virtualenv.")
            sys.exit(1)
    info("Installing google-play-scraper into the virtualenv ...")
    if not run([str(venv_py), "-m", "pip", "install", "--quiet",
                "--disable-pip-version-check", "google-play-scraper"]):
        err("Failed to install google-play-scraper.")
        sys.exit(1)
    reexec(str(venv_py), [str(venv_py), str(SCRIPT_PATH), *sys.argv[1:]])


def ensure_apkeep():
    """Install apkeep via cargo if missing. Falls back to brew/apt if available."""
    if shutil.which("apkeep"):
        return True

    info("apkeep not found. Attempting to install...")

    # Prefer cargo (official method)
    if shutil.which("cargo"):
        info("Using cargo to install apkeep (this may take a few minutes)...")
        if run(["cargo", "install", "apkeep"]):
            ok("apkeep installed via cargo")
            return True

    # Fallback: brew (macOS/Linux)
    if shutil.which("brew"):
        info("cargo not found, trying homebrew...")
        if run(["brew", "install", "apkeep"]):
            ok("apkeep installed via brew")
            return True

    err("Could not install apkeep automatically.")
    err("Install manually: https://github.com/EFForg/apkeep")
    err("  cargo install apkeep")
    err("  or: brew install apkeep")
    return False


def ensure_ipatool():
    """Install ipatool (iOS App Store) via brew/go if missing."""
    if shutil.which("ipatool"):
        return True

    info("ipatool not found. Attempting to install...")
    if shutil.which("brew"):
        if run(["brew", "install", "ipatool"]):
            ok("ipatool installed via brew")
            return True
    if shutil.which("go"):
        if run(["go", "install", "github.com/majd/ipatool/v2@latest"]):
            ok("ipatool installed via go")
            return True

    err("Could not install ipatool automatically.")
    err("Install manually: https://github.com/majd/ipatool")
    err("  brew install ipatool")
    return False


def ensure_dependencies(platform="android"):
    """Ensure all runtime dependencies are present for the chosen platform."""
    if platform == "ios":
        if not ensure_ipatool():
            sys.exit(1)
        return

    # 1. Rust/cargo (only needed if apkeep isn't already installed)
    if not shutil.which("apkeep") and not shutil.which("cargo"):
        warn("Neither apkeep nor cargo found.")
        if shutil.which("apt"):
            info("Attempting to install Rust via apt...")
            run(["sudo", "apt", "update"])
            run(["sudo", "apt", "install", "-y", "cargo"])
        elif shutil.which("brew"):
            info("Attempting to install Rust via brew...")
            run(["brew", "install", "rust"])

    # 2. apkeep itself
    if not ensure_apkeep():
        sys.exit(1)


# ---------- Config ----------
def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
    CONFIG_FILE.chmod(0o600)
    ok(f"Saved config to {CONFIG_FILE}")


def cmd_setup(args):
    if getattr(args, "platform", "android") == "ios":
        info("Signing in to the App Store via ipatool ...")
        sys.exit(subprocess.run(["ipatool", "auth", "login"]).returncode)

    cfg = load_config()
    print("Configure AppGrab (press Enter to keep existing value)\n")
    email = input(f"Google email [{cfg.get('email', '')}]: ").strip() or cfg.get("email", "")
    token = input(f"AAS token [{'set' if cfg.get('aas_token') else 'not set'}]: ").strip() or cfg.get("aas_token", "")
    outdir = input(f"Default output dir [{cfg.get('output', '.')}]: ").strip() or cfg.get("output", ".")
    cfg.update({"email": email, "aas_token": token, "output": outdir})
    save_config(cfg)
    print("\nGet an AAS token via: apkeep -e <email> --oauth-token '<oauth_token>'")


# ---------- Google Play search ----------
def gplay_search(term, limit):
    """Search Google Play using google-play-scraper (Python)."""
    from google_play_scraper import search
    results = search(term, lang="en", country="us", n_hits=limit)
    return [{"appId": r["appId"], "title": r["title"]}
            for r in results if r.get("appId")]


# ---------- iOS / App Store (ipatool) ----------
def iap_run(args, capture=False):
    """Run an ipatool sub-command in non-interactive JSON mode."""
    cmd = ["ipatool", *args, "--format", "json", "--non-interactive"]
    if capture:
        return subprocess.run(cmd, capture_output=True, text=True)
    return subprocess.run(cmd)


def iap_json(args):
    """Run ipatool and return the parsed JSON log object (or None)."""
    r = iap_run(args, capture=True)
    if r.returncode != 0:
        err(r.stderr.strip() or "ipatool command failed")
        return None
    for line in reversed(r.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


def iap_search(term, limit):
    """Search the App Store via ipatool (no auth required)."""
    data = iap_json(["search", term, "--limit", str(limit)])
    apps = (data or {}).get("apps", [])
    return [{"appId": a["bundleID"], "title": a.get("name", ""),
             "version": a.get("version", ""), "id": a.get("id")}
            for a in apps if a.get("bundleID")]


def iap_authenticated():
    data = iap_json(["auth", "info"])
    return bool(data and data.get("success"))


def require_iap_auth():
    if iap_authenticated():
        return
    err("Not signed in to the App Store.")
    err("Run: ipatool auth login   (or: appgrab.py setup -p ios)")
    sys.exit(1)


def iap_download_one(app_id, outdir, purchase=True, verbose=True):
    """Download a single .ipa by bundle id (or numeric app id)."""
    Path(outdir).mkdir(parents=True, exist_ok=True)
    id_flag = "-i" if str(app_id).isdigit() else "-b"
    args = ["download", id_flag, str(app_id), "-o", outdir]
    if purchase:
        args.append("--purchase")

    if verbose:
        info(f"Downloading {app_id} ...")
    r = iap_run(args)
    if r.returncode == 0:
        if verbose:
            ok(f"Done: {app_id}")
    else:
        err(f"ipatool exited with code {r.returncode} for {app_id}")
    return r.returncode


def iap_download_bulk(app_ids, outdir, parallel, purchase=True):
    Path(outdir).mkdir(parents=True, exist_ok=True)
    workers = max(1, parallel)
    info(f"Downloading {len(app_ids)} apps from the App Store (parallel={workers}) ...")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        codes = list(pool.map(
            lambda a: iap_download_one(a, outdir, purchase, verbose=False), app_ids))

    failed = [a for a, code in zip(app_ids, codes) if code != 0]
    if failed:
        err(f"{len(failed)}/{len(app_ids)} downloads failed: {', '.join(failed)}")
        return 1
    ok(f"All downloads complete. Files in: {os.path.abspath(outdir)}")
    return 0


# ---------- apkeep wrappers ----------
def download_single(app_id, cfg, source, outdir, parallel):
    Path(outdir).mkdir(parents=True, exist_ok=True)
    base = ["apkeep", "-a", app_id, "-d", source, "-r", str(parallel), "--accept-tos"]
    if source == "google-play":
        if not cfg.get("email") or not cfg.get("aas_token"):
            err("Google Play requires email + aas_token. Run: appgrab.py setup")
            sys.exit(1)
        base += ["-e", cfg["email"], "-t", cfg["aas_token"]]
    base.append(outdir)

    info(f"Downloading {app_id} ...")
    r = subprocess.run(base)
    if r.returncode == 0:
        ok(f"Done: {app_id}")
    else:
        err(f"apkeep exited with code {r.returncode} for {app_id}")
    return r.returncode


def download_bulk(app_ids, cfg, source, outdir, parallel):
    Path(outdir).mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        csv_path = f.name
        for app_id in app_ids:
            f.write(f"{app_id}\n")

    try:
        args = ["apkeep", "-c", csv_path, "-f", "1", "-d", source,
                "-r", str(parallel), "--accept-tos"]
        if source == "google-play":
            if not cfg.get("email") or not cfg.get("aas_token"):
                err("Google Play requires email + aas_token. Run: appgrab.py setup")
                sys.exit(1)
            args += ["-e", cfg["email"], "-t", cfg["aas_token"]]
        args.append(outdir)

        info(f"Downloading {len(app_ids)} apps from {source} (parallel={parallel}) ...")
        r = subprocess.run(args)
        if r.returncode == 0:
            ok(f"All downloads complete. Files in: {os.path.abspath(outdir)}")
        else:
            err(f"apkeep exited with code {r.returncode}")
        return r.returncode
    finally:
        os.unlink(csv_path)


# ---------- Commands ----------
def cmd_search_ios(args):
    cfg = load_config()
    outdir = args.output or cfg.get("output", ".")

    info(f'Searching the App Store for "{args.term}" (limit={args.limit}) ...')
    results = iap_search(args.term, args.limit)
    if not results:
        warn("No results.")
        return

    print()
    for i, r in enumerate(results, 1):
        version = f" (v{r['version']})" if r.get("version") else ""
        print(f"  {i:>2}. {c(r['appId'], '33'):<55}  {r['title']}{version}")
    print()

    if args.dry_run:
        info("Dry run — skipping downloads.")
        return

    if not args.yes:
        confirm = input(f"Download all {len(results)} apps to '{outdir}'? [y/N] ").strip().lower()
        if confirm not in ("y", "yes"):
            warn("Aborted.")
            return

    require_iap_auth()
    sys.exit(iap_download_bulk([r["appId"] for r in results], outdir,
                               args.parallel, purchase=args.purchase))


def cmd_search(args):
    if getattr(args, "platform", "android") == "ios":
        return cmd_search_ios(args)

    bootstrap_python_env()
    cfg = load_config()
    outdir = args.output or cfg.get("output", ".")
    # Default to apk-pure (free, no auth required)
    source = args.source or cfg.get("source", "apk-pure")

    info(f'Searching Google Play for "{args.term}" (limit={args.limit}) ...')
    results = gplay_search(args.term, args.limit)
    if not results:
        warn("No results.")
        return

    print()
    for i, r in enumerate(results, 1):
        print(f"  {i:>2}. {c(r['appId'], '33'):<50}  {r['title']}")
    print()

    if args.dry_run:
        info("Dry run — skipping downloads.")
        return

    if not args.yes:
        confirm = input(f"Download all {len(results)} apps to '{outdir}'? [y/N] ").strip().lower()
        if confirm not in ("y", "yes"):
            warn("Aborted.")
            return

    download_bulk([r["appId"] for r in results], cfg, source, outdir, args.parallel)


def cmd_download(args):
    cfg = load_config()
    outdir = args.output or cfg.get("output", ".")

    if getattr(args, "platform", "android") == "ios":
        require_iap_auth()
        sys.exit(iap_download_one(args.app_id, outdir, purchase=args.purchase))

    source = args.source or cfg.get("source", "apk-pure")
    sys.exit(download_single(args.app_id, cfg, source, outdir, args.parallel))


# ---------- CLI ----------
PLATFORMS = ["android", "ios"]
ANDROID_SOURCES = ["apk-pure", "google-play", "f-droid", "huawei-app-gallery"]


def add_platform(parser):
    parser.add_argument("-p", "--platform", choices=PLATFORMS, default="android",
                        help="App platform: android (APK/apkeep) or ios (IPA/ipatool)")


def add_purchase(parser):
    parser.add_argument("--purchase", action=argparse.BooleanOptionalAction, default=True,
                        help="iOS: acquire an App Store license if required (default: on)")


def main():
    p = argparse.ArgumentParser(
        prog="appgrab",
        description="Search and bulk-download Android APKs (apkeep) and iOS IPAs (ipatool). "
                    "Defaults to the free APKPure source.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("setup", help="Configure credentials (Google Play AAS token or App Store login)")
    add_platform(sp)
    sp.set_defaults(func=cmd_setup)

    sp = sub.add_parser("search", help="Search a store and download all results")
    sp.add_argument("term")
    add_platform(sp)
    add_purchase(sp)
    sp.add_argument("--limit", type=int, default=10)
    sp.add_argument("-o", "--output", default=None)
    sp.add_argument("-s", "--source", default="apk-pure", choices=ANDROID_SOURCES,
                    help="Android download source (ignored for -p ios)")
    sp.add_argument("-r", "--parallel", type=int, default=4)
    sp.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    sp.add_argument("--dry-run", action="store_true", help="Only list results, don't download")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("download", help="Download a single app (bundle/app id)")
    sp.add_argument("app_id")
    add_platform(sp)
    add_purchase(sp)
    sp.add_argument("-o", "--output", default=None)
    sp.add_argument("-s", "--source", default="apk-pure", choices=ANDROID_SOURCES,
                    help="Android download source (ignored for -p ios)")
    sp.add_argument("-r", "--parallel", type=int, default=4)
    sp.set_defaults(func=cmd_download)

    args = p.parse_args()
    ensure_dependencies(getattr(args, "platform", "android"))
    args.func(args)


if __name__ == "__main__":
    main()