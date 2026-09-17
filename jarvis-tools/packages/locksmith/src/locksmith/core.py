"""locksmith core: encrypted credential bundles over rclone.

Design constraints:
- Secret material never goes to stdout/stderr — callers print only paths,
  sizes, and timestamps.
- The Fernet key at ~/.config/locksmith/key is the ONE credential that
  must be hand-carried to a new box; everything else round-trips through
  the remote as a single encrypted tarball.
- Remote transport is `rclone` (the jarvis GCS route, same as ferry); a
  bare filesystem path works as a remote too, which the tests use.
"""

from __future__ import annotations

import io
import os
import stat
import subprocess
import tarfile
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet

CONFIG_DIR = Path(os.environ.get("LOCKSMITH_HOME", "~/.config/locksmith")).expanduser()
BUNDLE_NAME = "bundle.enc"

DEFAULT_CONFIG = """\
# locksmith config — which credential files sync, and where.
# Paths are relative to ~ (or absolute). The bundle is a single
# Fernet-encrypted tarball at <remote.url>/bundle.enc (+ timestamped
# copies under history/). The key at ~/.config/locksmith/key is NOT
# synced — hand-carry it to a new box, then `locksmith pull`.

[remote]
url = "gcs:alignment-team-general-storage/daniel/jarvis/locksmith"

[items]
paths = [
  "~/.env",
  "~/.config/rclone/rclone.conf",
  "~/.config/gcloud/application_default_credentials.json",
  "~/.config/gazette/config.toml",
  "~/.config/gh/hosts.yml",
  "~/.runpod/config.toml",
  "~/.runpod/ssh",
]
"""


def _config_path() -> Path:
    return CONFIG_DIR / "config.toml"


def _key_path() -> Path:
    return CONFIG_DIR / "key"


@dataclass
class Config:
    remote_url: str
    paths: list[Path]


def load_config() -> Config:
    path = _config_path()
    if not path.exists():
        raise SystemExit(f"no config at {path} — run `locksmith init`")
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    return Config(
        remote_url=raw["remote"]["url"].rstrip("/"),
        paths=[Path(p).expanduser() for p in raw["items"]["paths"]],
    )


def init(force: bool = False) -> list[str]:
    """Create key + default config if absent. `force` rewrites the config
    only — an existing key is never overwritten (rotating it would orphan
    the remote bundle; delete the key file explicitly if you mean it)."""
    actions = []
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CONFIG_DIR, stat.S_IRWXU)
    if not _key_path().exists():
        _key_path().write_bytes(Fernet.generate_key())
        os.chmod(_key_path(), stat.S_IRUSR | stat.S_IWUSR)
        actions.append(f"generated key {_key_path()}")
    if force or not _config_path().exists():
        _config_path().write_text(DEFAULT_CONFIG)
        actions.append(f"wrote default config {_config_path()}")
    return actions


def _fernet() -> Fernet:
    if not _key_path().exists():
        raise SystemExit(
            f"no key at {_key_path()} — run `locksmith init` "
            "(new box: copy the key from the old box first)"
        )
    return Fernet(_key_path().read_bytes())


def _rclone(*args: str) -> None:
    proc = subprocess.run(["rclone", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"rclone {args[0]} failed: {proc.stderr.strip()[-300:]}")


def make_bundle(cfg: Config) -> tuple[bytes, list[tuple[str, int]]]:
    """Tar existing items (arcnames relative to ~) and encrypt.

    Returns (ciphertext, [(display_path, size_bytes), ...]).
    """
    home = Path.home()
    buf = io.BytesIO()
    manifest: list[tuple[str, int]] = []
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for p in cfg.paths:
            if not p.exists():
                continue
            arcname = str(p.relative_to(home)) if p.is_relative_to(home) else str(p).lstrip("/")
            tar.add(p, arcname=arcname)
            manifest.append((str(p), p.stat().st_size))
    return _fernet().encrypt(buf.getvalue()), manifest


def push(cfg: Config) -> list[tuple[str, int]]:
    ciphertext, manifest = make_bundle(cfg)
    if not manifest:
        raise SystemExit("nothing to push — no manifest item exists locally")
    tmp = CONFIG_DIR / f".{BUNDLE_NAME}.tmp"
    tmp.write_bytes(ciphertext)
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    try:
        _rclone("copyto", str(tmp), f"{cfg.remote_url}/{BUNDLE_NAME}")
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        _rclone("copyto", str(tmp), f"{cfg.remote_url}/history/bundle-{stamp}.enc")
    finally:
        tmp.unlink(missing_ok=True)
    return manifest


def pull(cfg: Config, dest: Path | None = None) -> tuple[list[str], Path | None]:
    """Fetch, decrypt, extract under `dest` (default ~), backing up any
    files that would be overwritten. Returns (restored, backup_dir)."""
    dest = dest or Path.home()
    tmp = CONFIG_DIR / f".{BUNDLE_NAME}.dl"
    _rclone("copyto", f"{cfg.remote_url}/{BUNDLE_NAME}", str(tmp))
    try:
        plaintext = _fernet().decrypt(tmp.read_bytes())
    finally:
        tmp.unlink(missing_ok=True)

    backup_dir: Path | None = None
    restored: list[str] = []
    with tarfile.open(fileobj=io.BytesIO(plaintext), mode="r:gz") as tar:
        members = [m for m in tar.getmembers() if m.isfile()]
        for m in members:
            target = dest / m.name
            if target.exists():
                if backup_dir is None:
                    backup_dir = CONFIG_DIR / f"backup-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
                bak = backup_dir / m.name
                bak.parent.mkdir(parents=True, exist_ok=True)
                bak.write_bytes(target.read_bytes())
                os.chmod(bak, stat.S_IRUSR | stat.S_IWUSR)
        tar.extractall(dest, members=members, filter="data")
        for m in members:
            os.chmod(dest / m.name, stat.S_IRUSR | stat.S_IWUSR)
            restored.append(str(dest / m.name))
    return restored, backup_dir


def status(cfg: Config) -> dict:
    local = [(str(p), p.exists()) for p in cfg.paths]
    proc = subprocess.run(
        ["rclone", "lsl", f"{cfg.remote_url}/{BUNDLE_NAME}"], capture_output=True, text=True
    )
    remote = proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None
    return {
        "key": _key_path().exists(),
        "remote_url": cfg.remote_url,
        "remote_bundle": remote,
        "items": local,
    }
