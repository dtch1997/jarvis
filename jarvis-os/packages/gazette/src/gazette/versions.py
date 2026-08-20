"""JARVIS versions — nightly cuts of main, deployed to the box, switchable.

The consumer-mode bargain after the 2026-08-19 lane rework: PRs merge on
green continuously (hourly sweep), but the *box* changes once per night —
``version cut`` tags ``origin/main`` as ``vYYYY.MM.DD`` and ``version
deploy`` deploys that state (pull + the configured deploy_cmds: venv sync,
PATH links, crontab). Daniel's control is post-hoc: ``version switch
v2026.08.15`` pins the checkout to that tag and redeploys everything from
it (CLAUDE.md, crons, and CLIs roll back together); ``version switch
latest`` clears the pin and resumes nightly tracking. The pin survives
nightly deploys until cleared.

All git/subprocess I/O degrades to (ok=False, message) — a cron must log a
failure, never stack-trace. Pin state lives in ``~/.gazette/version-pin``.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from datetime import datetime
from pathlib import Path

from .config import Config, spool_dir

TAG_RE = re.compile(r"^v\d{4}\.\d{2}\.\d{2}(?:\.\d+)?$")


def _env() -> dict:
    """cron gets a minimal PATH; make sure ~/.local/bin (uv, gh, linked CLIs)
    is visible to git hooks and deploy_cmds alike."""
    env = dict(os.environ)
    local_bin = str(Path.home() / ".local" / "bin")
    if local_bin not in env.get("PATH", ""):
        env["PATH"] = f"{local_bin}:{env.get('PATH', '')}"
    return env


def _run(args: list[str], cwd: Path, timeout: int = 600) -> tuple[bool, str]:
    """Run a command; (ok, combined-output-or-error). Never raises."""
    try:
        proc = subprocess.run(
            args, cwd=str(cwd), env=_env(), capture_output=True, text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return False, f"{args[0]}: not found"
    except subprocess.TimeoutExpired:
        return False, f"{' '.join(args[:3])}: timed out"
    out = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0:
        return False, f"{' '.join(args[:3])} failed: {out[:400]}"
    return True, out


def _git(checkout: Path, *args: str) -> tuple[bool, str]:
    return _run(["git", *args], cwd=checkout, timeout=300)


def checkout_path(cfg: Config) -> Path:
    return Path(cfg.checkout).expanduser()


def toplevel(cfg: Config) -> Path | None:
    ok, out = _git(checkout_path(cfg), "rev-parse", "--show-toplevel")
    return Path(out) if ok else None


def pin_path() -> Path:
    return spool_dir() / "version-pin"


def current_pin() -> str | None:
    try:
        pin = pin_path().read_text().strip()
    except OSError:
        return None
    return pin or None


def _set_pin(tag: str | None) -> None:
    path = pin_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if tag is None:
        path.unlink(missing_ok=True)
    else:
        path.write_text(tag + "\n")


def list_versions(cfg: Config, limit: int = 15) -> tuple[list[dict], str | None]:
    """Newest-first [{tag, sha, date}]; (rows, warning)."""
    # %(*objectname) is the peeled commit for annotated tags (what a human
    # wants to see) and empty for lightweight ones — fall back to %(objectname).
    ok, out = _git(
        checkout_path(cfg), "tag", "--list", "v*", "--sort=-v:refname",
        "--format=%(refname:short) %(objectname:short) %(*objectname:short) %(creatordate:short)",
    )
    if not ok:
        return [], out
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) in (3, 4) and TAG_RE.match(parts[0]):
            rows.append({"tag": parts[0], "sha": parts[-2], "date": parts[-1]})
    return rows[:limit], None


def _next_tag(existing: set[str], now: datetime) -> str:
    base = f"v{now:%Y.%m.%d}"
    if base not in existing:
        return base
    n = 2
    while f"{base}.{n}" in existing:
        n += 1
    return f"{base}.{n}"


def cut(cfg: Config, now: datetime | None = None) -> tuple[bool, str]:
    """Tag origin/main's current tip as tonight's version and push the tag.
    Idempotent: if the newest version tag already points at that tip, no-op."""
    now = now or datetime.now()
    co = checkout_path(cfg)
    ok, msg = _git(co, "fetch", "--tags", "-q", "origin")
    if not ok:
        return False, f"cut: {msg}"
    ok, tip = _git(co, "rev-parse", "origin/main")
    if not ok:
        return False, f"cut: {tip}"
    versions, warn = list_versions(cfg, limit=10000)
    if warn:
        return False, f"cut: {warn}"
    if versions:
        ok, latest_sha = _git(co, "rev-parse", versions[0]["tag"] + "^{commit}")
        if ok and latest_sha == tip:
            return True, f"cut: no changes since {versions[0]['tag']} — nothing to cut"
    tag = _next_tag({v["tag"] for v in versions}, now)
    ok, msg = _git(co, "tag", "-a", tag, tip, "-m", f"jarvis nightly cut {tag}")
    if not ok:
        return False, f"cut: {msg}"
    ok, msg = _git(co, "push", "-q", "origin", tag)
    if not ok:
        return False, f"cut: tagged {tag} locally but push failed — {msg}"
    return True, f"cut: {tag} @ {tip[:9]}"


def deploy(cfg: Config) -> tuple[bool, list[str]]:
    """Deploy the pinned version (detached at its tag) or, unpinned, main's
    nightly state (ff-only pull). Then run deploy_cmds at the git toplevel so
    venv/CLIs/crontab match the deployed tree. Returns (ok, report lines)."""
    co = checkout_path(cfg)
    lines: list[str] = []
    ok, msg = _git(co, "fetch", "--tags", "-q", "origin")
    if not ok:
        return False, [f"deploy: {msg}"]
    pin = current_pin()
    if pin:
        ok, _ = _git(co, "rev-parse", "--verify", pin + "^{commit}")
        if not ok:
            return False, [f"deploy: pinned to {pin!r} but no such tag exists — "
                           f"fix with `gazette version switch <tag|latest>`"]
        ok, msg = _git(co, "checkout", "-q", "--detach", pin)
        if not ok:
            return False, [f"deploy: {msg}"]
        lines.append(f"deploy: PINNED — checked out {pin} (detached); "
                     "resume nightly tracking with `gazette version switch latest`")
    else:
        ok, msg = _git(co, "checkout", "-q", "main")
        if not ok:
            return False, [f"deploy: {msg}"]
        ok, msg = _git(co, "pull", "--ff-only", "-q")
        if not ok:
            return False, [f"deploy: {msg}"]
        ok, head = _git(co, "rev-parse", "--short", "HEAD")
        lines.append(f"deploy: main @ {head if ok else '?'}")
    top = toplevel(cfg)
    if top is None:
        return False, lines + ["deploy: could not resolve git toplevel"]
    for cmd in cfg.deploy_cmds:
        ok, msg = _run(shlex.split(cmd), cwd=top)
        lines.append(f"deploy: `{cmd}` {'ok' if ok else 'FAILED — ' + msg}")
        if not ok:
            return False, lines
    return True, lines


def switch(cfg: Config, target: str) -> tuple[bool, list[str]]:
    """Pin the box to a version tag (rollback), or ``latest``/``main`` to
    resume nightly tracking. Redeploys immediately either way."""
    co = checkout_path(cfg)
    _git(co, "fetch", "--tags", "-q", "origin")
    if target in ("latest", "main"):
        _set_pin(None)
        ok, lines = deploy(cfg)
        return ok, [f"switch: unpinned — tracking nightly versions again"] + lines
    if not TAG_RE.match(target):
        return False, [f"switch: {target!r} is not a version tag (vYYYY.MM.DD) or 'latest'"]
    ok, _ = _git(co, "rev-parse", "--verify", target + "^{commit}")
    if not ok:
        return False, [f"switch: no such version {target!r} — see `gazette version list`"]
    _set_pin(target)
    ok, lines = deploy(cfg)
    return ok, [f"switch: pinned to {target}"] + lines


def status(cfg: Config) -> str:
    """One line: what the box is running, pin state, whether main moved on."""
    co = checkout_path(cfg)
    ok, head = _git(co, "rev-parse", "--short", "HEAD")
    if not ok:
        return f"version status unavailable ({head})"
    ok, tags = _git(co, "tag", "--points-at", "HEAD", "--list", "v*")
    here = ", ".join(t for t in tags.splitlines() if TAG_RE.match(t)) if ok else ""
    versions, _ = list_versions(cfg, limit=1)
    latest = versions[0]["tag"] if versions else None
    pin = current_pin()
    running = here or f"main @ {head}"
    if pin:
        behind = f"; latest is {latest}" if latest and latest != pin else ""
        return (f"running {running} — PINNED to {pin}{behind} "
                f"(resume: gazette version switch latest)")
    return f"running {running}" + (f" (latest cut: {latest})" if latest and latest not in (here or "") else "")
