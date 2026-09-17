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
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

__version__ = "1.2.0"

REPO_SLUG = os.environ.get("APPGRAB_REPO", "iamhsouna/appgrab")
REPO_URL = f"https://github.com/{REPO_SLUG}"
REF = os.environ.get("APPGRAB_REF", "main")

CONFIG_DIR = Path.home() / ".config" / "appgrab"
CONFIG_FILE = CONFIG_DIR / "config.json"

SCRIPT_PATH = Path(__file__).resolve()
BOOTSTRAP_ENV = "_APPGRAB_BOOTSTRAPPED"
VENV_DIR = Path(os.environ.get("APPGRAB_VENV", Path.home() / ".cache" / "appgrab" / "venv"))

LOCAL_BIN = Path.home() / ".local" / "bin"
ASSUME_YES = os.environ.get("APPGRAB_YES", "").lower() in ("1", "true", "yes")


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


def confirm(question, default=True):
    """Ask the user for confirmation before installing something."""
    if ASSUME_YES:
        info(f"{question} (auto-yes)")
        return True
    if not sys.stdin.isatty():
        info(f"{question} (non-interactive: yes)")
        return True
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            answer = input(f"{c('?', '35')} {question} {suffix} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return default
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        warn("Please answer 'y' or 'n'.")


def ensure_local_bin_on_path():
    """Put ~/.local/bin, ~/.cargo/bin and ~/go/bin on PATH if they exist."""
    path = os.environ.get("PATH", "").split(os.pathsep)
    for extra in (LOCAL_BIN, Path.home() / ".cargo" / "bin", Path.home() / "go" / "bin"):
        if extra.is_dir() and str(extra) not in path:
            os.environ["PATH"] = f"{extra}{os.pathsep}{os.environ.get('PATH', '')}"
            path.insert(0, str(extra))


def os_name():
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("linux"):
        if os.path.exists("/etc/arch-release") or shutil.which("pacman"):
            return "arch"
        if os.path.exists("/etc/debian_version") or shutil.which("apt-get"):
            return "debian"
        return "linux"
    return sys.platform


def cpu_arch():
    machine = platform.machine().lower()
    return {"arm64": "arm64", "aarch64": "arm64",
            "x86_64": "amd64", "amd64": "amd64",
            "armv7l": "armv7", "i386": "i686", "i686": "i686"}.get(machine, machine)


def pkg_manager():
    """Return the best available system package manager name."""
    if sys.platform == "darwin":
        return "brew" if shutil.which("brew") else None
    for pm in ("pacman", "apt-get", "dnf", "zypper", "brew"):
        if shutil.which(pm):
            return pm
    return None


PKG_NAMES = {
    "rust": {"brew": "rust", "apt-get": "cargo", "pacman": "rust", "dnf": "cargo", "zypper": "cargo"},
    "go":   {"brew": "go",   "apt-get": "golang-go", "pacman": "go", "dnf": "golang", "zypper": "go"},
    "venv": {"brew": "python", "apt-get": "python3-venv", "pacman": "python", "dnf": "python3", "zypper": "python3"},
}


def system_install(packages):
    """Install system packages with the detected package manager."""
    pm = pkg_manager()
    if not pm:
        warn("No supported package manager found (brew / apt / pacman / dnf / zypper).")
        return False
    if pm == "apt-get":
        run(["sudo", "apt-get", "update"])
        cmd = ["sudo", "apt-get", "install", "-y", *packages]
    elif pm == "pacman":
        cmd = ["sudo", "pacman", "-S", "--needed", "--noconfirm", *packages]
    elif pm == "dnf":
        cmd = ["sudo", "dnf", "install", "-y", *packages]
    elif pm == "zypper":
        cmd = ["sudo", "zypper", "--non-interactive", "install", *packages]
    else:  # brew
        cmd = ["brew", "install", *packages]
    info(f"Running: {' '.join(cmd)}")
    return run(cmd)


# ---------- GitHub release downloads (no compiler needed) ----------
def _github_latest_asset(repo, predicate):
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "appgrab",
                                               "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
    except Exception as exc:  # noqa: BLE001
        warn(f"GitHub API request failed for {repo}: {exc}")
        return None, None
    for asset in data.get("assets", []):
        if predicate(asset["name"]):
            return asset["name"], asset["browser_download_url"]
    return None, None


def _download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "appgrab"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as handle:
        shutil.copyfileobj(resp, handle)


def _fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "appgrab"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode()


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def install_from_release(repo, asset_predicate, binary_name, checksum_predicate=None):
    """Download a prebuilt binary (raw or .tar.gz) from a GitHub release."""
    name, url = _github_latest_asset(repo, asset_predicate)
    if not url:
        warn(f"No prebuilt binary available for this platform in {repo}.")
        return False

    LOCAL_BIN.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix="appgrab-"))
    try:
        download = workdir / name
        info(f"Downloading {name} ...")
        _download(url, download)

        if checksum_predicate:
            _, checksum_url = _github_latest_asset(repo, checksum_predicate)
            if checksum_url:
                try:
                    expected = _fetch_text(checksum_url).split()[0]
                    if expected.lower() != _sha256(download).lower():
                        err("Checksum mismatch - aborting install.")
                        return False
                    ok("Checksum verified.")
                except Exception as exc:  # noqa: BLE001
                    warn(f"Could not verify checksum: {exc}")

        target = LOCAL_BIN / binary_name
        if name.endswith((".tar.gz", ".tgz")):
            with tarfile.open(download, "r:gz") as archive:
                files = [m for m in archive.getmembers() if m.isfile()]
                member = next((m for m in files
                               if m.name.split("/")[-1].startswith(binary_name)), None)
                if member is None and len(files) == 1:
                    member = files[0]
                if member is None:
                    err(f"{binary_name} not found inside {name}.")
                    return False
                with archive.extractfile(member) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        else:
            shutil.copy2(download, target)

        target.chmod(0o755)
        ok(f"Installed {binary_name} -> {target}")
        return True
    except Exception as exc:  # noqa: BLE001
        err(f"Download/install failed: {exc}")
        return False
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def have_google_play_scraper():
    try:
        import google_play_scraper  # noqa: F401
        return True
    except ImportError:
        return False


def ensure_venv_support():
    """Offer to install Python's venv module when it is unavailable."""
    pm = pkg_manager()
    packages = PKG_NAMES["venv"].get(pm, [])
    if not packages:
        return False
    warn("Creating a virtualenv failed; the 'venv' module may be missing.")
    if not confirm("Install Python virtualenv support via the system package manager?"):
        return False
    return system_install([packages])


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

    warn("Python dependency 'google-play-scraper' is missing.")
    if not confirm("Set up an isolated Python environment and install it now?"):
        err("Cannot continue without google-play-scraper.")
        sys.exit(1)
    os.environ[BOOTSTRAP_ENV] = "1"

    ensure_local_bin_on_path()

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
        created = run([sys.executable, "-m", "venv", str(VENV_DIR)])
        if not created and ensure_venv_support():
            created = run([sys.executable, "-m", "venv", str(VENV_DIR)])
        if not created:
            err("Failed to create virtualenv.")
            sys.exit(1)
    info("Installing google-play-scraper into the virtualenv ...")
    if not run([str(venv_py), "-m", "pip", "install", "--quiet",
                "--disable-pip-version-check", "google-play-scraper"]):
        err("Failed to install google-play-scraper.")
        sys.exit(1)
    reexec(str(venv_py), [str(venv_py), str(SCRIPT_PATH), *sys.argv[1:]])


def ensure_rust():
    """Make cargo available, installing the Rust toolchain if the user agrees."""
    if shutil.which("cargo"):
        return True
    warn("Rust/cargo is required to build apkeep from source.")
    if not confirm("Install the Rust toolchain now?"):
        return False
    ensure_local_bin_on_path()
    packages = PKG_NAMES["rust"].get(pkg_manager())
    if packages and system_install([packages]):
        ensure_local_bin_on_path()
        if shutil.which("cargo"):
            return True
    if shutil.which("curl"):
        info("Installing Rust via rustup ...")
        if run("curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y", shell=True):
            ensure_local_bin_on_path()
            return shutil.which("cargo") is not None
    return False


def ensure_go():
    """Make the Go toolchain available, installing it if the user agrees."""
    if shutil.which("go"):
        return True
    warn("Go is required to build ipatool from source.")
    if not confirm("Install the Go toolchain now?"):
        return False
    ensure_local_bin_on_path()
    packages = PKG_NAMES["go"].get(pkg_manager())
    if packages and system_install([packages]):
        ensure_local_bin_on_path()
        if shutil.which("go"):
            return True
    return False


def install_tool(display, check, strategies, manual_hint):
    """Install a native tool, asking first and trying each strategy in order."""
    if check():
        return True

    warn(f"{display} is not installed.")
    if not confirm(f"Install {display} now?"):
        err(f"Skipped {display}. Install manually: {manual_hint}")
        return False

    for label, action in strategies:
        info(f"Trying to install {display} via {label} ...")
        try:
            if action():
                ensure_local_bin_on_path()
                if check():
                    ok(f"{display} installed via {label}.")
                    return True
        except Exception as exc:  # noqa: BLE001
            warn(f"{label} failed: {exc}")

    err(f"Could not install {display} automatically. Install manually: {manual_hint}")
    return False


def apkeep_strategies():
    """Install strategies for apkeep, cross-platform."""
    triples = {"amd64": "x86_64-unknown-linux-gnu",
               "arm64": "aarch64-unknown-linux-gnu",
               "armv7": "armv7-unknown-linux-gnueabihf",
               "i686": "i686-unknown-linux-gnu"}
    triple = triples.get(cpu_arch())
    strategies = []

    if shutil.which("brew"):
        strategies.append(("homebrew", lambda: run(["brew", "install", "apkeep"])))
    if sys.platform.startswith("linux") and triple:
        strategies.append(("prebuilt binary", lambda t=triple: install_from_release(
            "EFForg/apkeep", lambda name, t=t: name == f"apkeep-{t}", "apkeep")))
    if shutil.which("cargo"):
        strategies.append(("cargo", lambda: run(["cargo", "install", "apkeep"])))
    strategies.append(("rust + cargo",
                       lambda: ensure_rust() and run(["cargo", "install", "apkeep"])))
    return strategies


def ipatool_strategies():
    """Install strategies for ipatool, cross-platform."""
    os_tag = {"macos": "macos", "arch": "linux", "debian": "linux", "linux": "linux"}.get(os_name())
    arch = cpu_arch()
    strategies = []

    if os_tag and arch in ("amd64", "arm64"):
        suffix = f"-{os_tag}-{arch}.tar.gz"

        def predicate(name, suffix=suffix):
            return name.endswith(suffix)

        strategies.append(("prebuilt binary", lambda p=predicate, s=suffix: install_from_release(
            "majd/ipatool", p, "ipatool",
            checksum_predicate=lambda name, s=s: name.endswith(s + ".sha256sum"))))
    if shutil.which("brew"):
        strategies.append(("homebrew", lambda: run(["brew", "install", "ipatool"])))
    if shutil.which("go"):
        strategies.append(("go", lambda: run(
            ["go", "install", "github.com/majd/ipatool/v2@latest"])))
    strategies.append(("go (install toolchain)",
                       lambda: ensure_go() and run(
                           ["go", "install", "github.com/majd/ipatool/v2@latest"])))
    return strategies


def ensure_dependencies(platform_name="android"):
    """Ensure all runtime dependencies are present for the chosen platform."""
    ensure_local_bin_on_path()

    if platform_name == "ios":
        ok_install = install_tool(
            "ipatool",
            lambda: shutil.which("ipatool") is not None,
            ipatool_strategies(),
            "https://github.com/majd/ipatool (brew install ipatool / go install ...)")
        if not ok_install:
            sys.exit(1)
        return

    ok_install = install_tool(
        "apkeep",
        lambda: shutil.which("apkeep") is not None,
        apkeep_strategies(),
        "https://github.com/EFForg/apkeep (brew install apkeep / cargo install apkeep)")
    if not ok_install:
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
        sys.exit(subprocess.run(["ipatool", "auth", "login"], check=False).returncode)

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
        return subprocess.run(cmd, capture_output=True, text=True, check=False)
    return subprocess.run(cmd, check=False)


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

    pool = ThreadPoolExecutor(max_workers=workers)
    try:
        codes = list(pool.map(
            lambda a: iap_download_one(a, outdir, purchase, verbose=False), app_ids))
    except KeyboardInterrupt:
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    else:
        pool.shutdown(wait=True)

    failed = [a for a, code in zip(app_ids, codes) if code != 0]
    if failed:
        err(f"{len(failed)}/{len(app_ids)} downloads failed: {', '.join(failed)}")
        return 1
    ok(f"All downloads complete. Files in: {os.path.abspath(outdir)}")
    return 0


# ---------- apkeep wrappers ----------
# When a source cannot provide an app, retry it from the fallback source.
FALLBACK_SOURCES = {"google-play": "huawei-app-gallery",
                    "apk-pure": "huawei-app-gallery"}


def source_chain(source, fallback=True):
    """Ordered list of sources to try: the chosen one, then its fallback."""
    chain = [source]
    if fallback:
        alt = FALLBACK_SOURCES.get(source)
        if alt and alt not in chain:
            chain.append(alt)
    return chain


def _apkeep_args(source, cfg, parallel):
    """Build the common apkeep arguments, or None when credentials are missing."""
    args = ["apkeep", "-d", source, "-r", str(parallel), "--accept-tos"]
    if source == "google-play":
        if not cfg.get("email") or not cfg.get("aas_token"):
            return None
        args += ["-e", cfg["email"], "-t", cfg["aas_token"]]
    return args


def download_one_android(app_id, cfg, source, outdir, parallel, fallback=True, verbose=True):
    """Download a single APK, falling back to Huawei AppGallery when configured.

    apkeep can exit 0 without fetching anything (e.g. "Could not get download
    URL ... Skipping..."), so success is judged by whether a file was produced.
    """
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    chain = source_chain(source, fallback)
    for i, src in enumerate(chain):
        if i:
            warn(f"{app_id} not available via {chain[i - 1]}; trying {src} ...")
        args = _apkeep_args(src, cfg, parallel)
        if args is None:
            err(f"{src} requires email + aas_token. Run: appgrab.py setup")
            continue
        if verbose:
            info(f"Downloading {app_id} from {src} ...")
        workdir = Path(tempfile.mkdtemp(prefix=".appgrab-", dir=str(out)))
        try:
            code = subprocess.run(args + ["-a", app_id, str(workdir)],
                                  check=False).returncode
            produced = [p for p in workdir.rglob("*") if p.is_file()]
            if produced:
                for path in produced:
                    shutil.move(str(path), str(out / path.name))
                if verbose:
                    ok(f"Done: {app_id} ({src})")
                return 0
            err(f"No APK produced for {app_id} via {src} (apkeep exit {code})")
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
    return 1


def download_single(app_id, cfg, source, outdir, parallel, fallback=True):
    return download_one_android(app_id, cfg, source, outdir, parallel, fallback)


def download_bulk(app_ids, cfg, source, outdir, parallel, fallback=True):
    Path(outdir).mkdir(parents=True, exist_ok=True)
    workers = max(1, parallel)
    chain = source_chain(source, fallback)
    suffix = f" (fallback: {chain[1]})" if len(chain) > 1 else ""
    info(f"Downloading {len(app_ids)} apps from {source}{suffix} (parallel={workers}) ...")

    pool = ThreadPoolExecutor(max_workers=workers)
    try:
        codes = list(pool.map(
            lambda a: download_one_android(a, cfg, source, outdir, 1, fallback, verbose=False),
            app_ids))
    except KeyboardInterrupt:
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    else:
        pool.shutdown(wait=True)

    failed = [a for a, code in zip(app_ids, codes) if code != 0]
    if failed:
        err(f"{len(failed)}/{len(app_ids)} downloads failed: {', '.join(failed)}")
        return 1
    ok(f"All downloads complete. Files in: {os.path.abspath(outdir)}")
    return 0


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

    if not confirm(f"Download all {len(results)} apps to '{outdir}'?", default=False):
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

    if not confirm(f"Download all {len(results)} apps to '{outdir}'?", default=False):
        warn("Aborted.")
        return

    download_bulk([r["appId"] for r in results], cfg, source, outdir,
                  args.parallel, fallback=args.fallback)


def cmd_download(args):
    cfg = load_config()
    outdir = args.output or cfg.get("output", ".")

    if getattr(args, "platform", "android") == "ios":
        require_iap_auth()
        sys.exit(iap_download_one(args.app_id, outdir, purchase=args.purchase))

    source = args.source or cfg.get("source", "apk-pure")
    sys.exit(download_single(args.app_id, cfg, source, outdir,
                             args.parallel, fallback=args.fallback))


# ---------- Update ----------
def parse_version(text):
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)', text, re.MULTILINE)
    return match.group(1) if match else None


def fetch_remote_script():
    """Fetch the latest appgrab.py from GitHub (works with private repos)."""
    if shutil.which("gh"):
        result = subprocess.run(
            ["gh", "api", f"repos/{REPO_SLUG}/contents/appgrab.py?ref={REF}",
             "-H", "Accept: application/vnd.github.raw"],
            capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPO_SLUG}/contents/appgrab.py?ref={REF}",
        headers={"User-Agent": "appgrab", "Accept": "application/vnd.github.raw"})
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read().decode()
    except Exception as exc:  # noqa: BLE001
        warn(f"Could not fetch the latest version: {exc}")
        return None


def tool_is_installed(manager, name):
    if manager == "uv":
        result = subprocess.run(["uv", "tool", "list"], capture_output=True, text=True, check=False)
    else:
        result = subprocess.run(["pipx", "list", "--short"], capture_output=True, text=True, check=False)
    return result.returncode == 0 and bool(re.search(rf"\b{re.escape(name)}\b", result.stdout))


def update_single_file():
    """Replace this running script with the latest version from GitHub."""
    info("Checking for a newer version ...")
    remote = fetch_remote_script()
    if not remote:
        err("Could not download the update (private repo? run 'gh auth login' or set GITHUB_TOKEN).")
        return 1

    remote_version = parse_version(remote)
    if remote_version and remote_version == __version__:
        ok(f"Already up to date (v{__version__}).")
        return 0

    dest = SCRIPT_PATH
    tmp = dest.with_name(dest.name + ".new")
    try:
        tmp.write_text(remote)
        tmp.chmod(0o755)
        os.replace(tmp, dest)
    except OSError as exc:
        err(f"Failed to write update: {exc}")
        tmp.unlink(missing_ok=True)
        return 1
    ok(f"Updated v{__version__} -> v{remote_version or 'latest'} ({dest}).")
    return 0


def cmd_update(args):
    ensure_local_bin_on_path()
    info(f"AppGrab v{__version__} ({SCRIPT_PATH})")

    if args.check:
        remote = fetch_remote_script()
        if not remote:
            err("Could not check for updates (private repo? run 'gh auth login' or set GITHUB_TOKEN).")
            return 1
        remote_version = parse_version(remote) or "unknown"
        if remote_version == __version__:
            ok(f"Up to date (v{__version__}).")
        else:
            warn(f"Update available: v{__version__} -> v{remote_version}.")
        return 0

    # 1) Running from a git checkout.
    repo_dir = SCRIPT_PATH.parent
    if (repo_dir / ".git").is_dir() and shutil.which("git"):
        info("Updating git checkout ...")
        code = subprocess.run(["git", "-C", str(repo_dir), "pull", "--ff-only"],
                              check=False).returncode
        if code == 0:
            ok("Git checkout updated.")
        else:
            err("git pull failed - resolve it manually in the repository.")
        return code

    # 2) Installed as a uv tool.
    if shutil.which("uv") and tool_is_installed("uv", "appgrab"):
        info("Updating with 'uv tool' ...")
        code = subprocess.run(["uv", "tool", "upgrade", "appgrab"], check=False).returncode
        if code != 0:
            code = subprocess.run(["uv", "tool", "install", "--force", f"git+{REPO_URL}"],
                                  check=False).returncode
        if code == 0:
            ok("AppGrab updated.")
        return code

    # 3) Installed as a pipx tool.
    if shutil.which("pipx") and tool_is_installed("pipx", "appgrab"):
        info("Updating with pipx ...")
        code = subprocess.run(["pipx", "install", "--force", f"git+{REPO_URL}"],
                              check=False).returncode
        if code == 0:
            ok("AppGrab updated.")
        return code

    # 4) Standalone single-file install.
    return update_single_file()


# ---------- CLI ----------
PLATFORMS = ["android", "ios"]
ANDROID_SOURCES = ["apk-pure", "google-play", "f-droid", "huawei-app-gallery"]


def add_platform(parser):
    parser.add_argument("-p", "--platform", choices=PLATFORMS, default="android",
                        help="App platform: android (APK/apkeep) or ios (IPA/ipatool)")


def add_purchase(parser):
    parser.add_argument("--purchase", action=argparse.BooleanOptionalAction, default=True,
                        help="iOS: acquire an App Store license if required (default: on)")


def add_yes(parser):
    parser.add_argument("-y", "--yes", action="store_true", default=argparse.SUPPRESS,
                        help="Assume 'yes' for install/download prompts")


def add_fallback(parser):
    parser.add_argument("--fallback", action=argparse.BooleanOptionalAction, default=True,
                        help="Fall back to Huawei AppGallery when the chosen source "
                             "can't provide an app (default: on)")


def main():
    p = argparse.ArgumentParser(
        prog="appgrab",
        description="Search and bulk-download Android APKs (apkeep) and iOS IPAs (ipatool). "
                    "Missing dependencies are installed on demand.",
    )
    p.add_argument("-y", "--yes", action="store_true",
                   help="Assume 'yes' for install/download prompts")
    p.add_argument("-V", "--version", action="version", version=f"appgrab {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("setup", help="Configure credentials (Google Play AAS token or App Store login)")
    add_platform(sp)
    add_yes(sp)
    sp.set_defaults(func=cmd_setup)

    sp = sub.add_parser("search", help="Search a store and download all results")
    sp.add_argument("term")
    add_platform(sp)
    add_purchase(sp)
    add_yes(sp)
    add_fallback(sp)
    sp.add_argument("--limit", type=int, default=10)
    sp.add_argument("-o", "--output", default=None)
    sp.add_argument("-s", "--source", default="apk-pure", choices=ANDROID_SOURCES,
                    help="Android download source (ignored for -p ios)")
    sp.add_argument("-r", "--parallel", type=int, default=4)
    sp.add_argument("--dry-run", action="store_true", help="Only list results, don't download")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("download", help="Download a single app (bundle/app id)")
    sp.add_argument("app_id")
    add_platform(sp)
    add_purchase(sp)
    add_yes(sp)
    add_fallback(sp)
    sp.add_argument("-o", "--output", default=None)
    sp.add_argument("-s", "--source", default="apk-pure", choices=ANDROID_SOURCES,
                    help="Android download source (ignored for -p ios)")
    sp.add_argument("-r", "--parallel", type=int, default=4)
    sp.set_defaults(func=cmd_download)

    sp = sub.add_parser("update", help="Update AppGrab to the latest version")
    sp.add_argument("--check", action="store_true", help="Only report whether an update is available")
    sp.set_defaults(func=cmd_update)

    try:
        args = p.parse_args()
        global ASSUME_YES
        if getattr(args, "yes", False):
            ASSUME_YES = True
        if args.cmd != "update":
            ensure_dependencies(getattr(args, "platform", "android"))
        sys.exit(args.func(args) or 0)
    except KeyboardInterrupt:
        print()
        warn("Interrupted.")
        sys.exit(130)


if __name__ == "__main__":
    main()