"""The harness publish-pass (issue #8): push a sandboxed worker's branch and
open its PR on its behalf.

The codex backend runs workers in a sandbox that keeps `.git` read-only and
blocks the network (see backends/codex.py), so a codex worker can *do* the work
but can neither `git push` nor reach GitHub. Policy (Daniel, 2026-08-18): codex
workers get write-your-workspace and nothing else; anything that crosses the
machine boundary — push, PR, artifact upload — is the harness's job. This module
is that job for push+PR.

The reconciler calls `publish_branch` after a codex worker exits and the LOCAL
components of its gate pass (the worker really did the work), then re-evaluates
the full gate — which now finds an open PR. Everything here is idempotent: it
re-checks for an existing PR before opening one, so a re-run (resume, restart)
never opens a duplicate.

The GitHub touch is isolated to `gh` (the PR-open/-view step); `git push` goes
to the workspace's own `origin`. Both are seams tests fill with a local bare
repo as origin and a stub `gh` on PATH — no live GitHub in unit tests.
"""
from __future__ import annotations

import json
import subprocess

from .records import Home, now_iso

PUBLISH_FOOTER = (
    "\n\n---\n🤖 Opened by the concierge harness on the worker's behalf "
    "(sandboxed backend: the worker did the work but its sandbox cannot push "
    "or reach GitHub — see dtch1997/jarvis#8)."
)


class PublishError(RuntimeError):
    """A push or PR-open step failed; the reconciler logs it and lets the gate
    fail normally (the PR won't be open, so PrOpen won't pass)."""


def _git(ws, *args, timeout=120) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ws), *args],
                          capture_output=True, text=True, timeout=timeout)


def has_commits(ws, base: str) -> bool:
    """True iff the workspace branch has at least one commit beyond its base —
    the guard against publishing an empty branch (a worker that didn't do the
    work). Tries the local base ref, then origin/<base>."""
    for ref in (base, f"origin/{base}"):
        r = _git(ws, "rev-list", "--count", f"{ref}..HEAD")
        if r.returncode == 0:
            try:
                return int(r.stdout.strip()) > 0
            except ValueError:
                return False
    return False


def _existing_pr(ws, branch: str, gh_bin: str) -> str | None:
    """The URL of an already-open PR for the branch, or None. Idempotency hinges
    on this: publish is a no-op (bar an up-to-date push) once a PR exists."""
    r = subprocess.run([gh_bin, "pr", "view", branch, "--json", "state,url"],
                       cwd=str(ws), capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return None
    try:
        info = json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return None
    return info.get("url") if info.get("state") == "OPEN" else None


def _pr_body(task: dict, notes: str | None, output: dict | None) -> str:
    parts: list[str] = []
    if output:
        parts.append("```json\n" + json.dumps(output, indent=2, default=str) + "\n```")
    if notes and notes.strip():
        parts.append(notes.strip())
    if not parts:
        parts.append(f"Automated publish for pool task `{task['id']}` — {task['title']}.")
    return "\n\n".join(parts) + PUBLISH_FOOTER


def publish_branch(home: Home, cfg: dict, task: dict, *,
                   notes: str | None = None, output: dict | None = None) -> dict:
    """Push the task's workspace branch to origin (never force, never to
    main/master) and open a PR for it; return {branch, pr_url, at}. Idempotent:
    an already-open PR is returned as-is without a second `gh pr create`.

    Raises PublishError on a push failure, a refused branch, or a PR-open
    failure — the caller treats that as a normal (unpublished) gate failure."""
    ws = home.workspace(task["id"])
    w = task["workspace"]
    branch, base = w["branch"], w.get("base", "main")
    gh_bin = cfg.get("gh_bin", "gh")

    if branch in ("main", "master") or base is None:
        raise PublishError(f"refusing to publish branch {branch!r} (base={base!r})")

    # push first (fast-forward, never force) so an existing PR also picks up any
    # new commits from a resumed attempt; a brand-new branch is created on origin
    push = _git(ws, "push", "origin", f"{branch}:{branch}")
    if push.returncode != 0:
        raise PublishError(f"git push failed: {(push.stderr or push.stdout).strip()[:300]}")

    existing = _existing_pr(ws, branch, gh_bin)
    if existing:
        return {"branch": branch, "pr_url": existing, "at": now_iso()}

    create = subprocess.run(
        [gh_bin, "pr", "create", "--head", branch, "--base", base,
         "--title", task["title"], "--body", _pr_body(task, notes, output)],
        cwd=str(ws), capture_output=True, text=True, timeout=180)
    if create.returncode != 0:
        # lost a race (a PR appeared between our check and create)? recover it
        recovered = _existing_pr(ws, branch, gh_bin)
        if recovered:
            return {"branch": branch, "pr_url": recovered, "at": now_iso()}
        raise PublishError(f"gh pr create failed: {(create.stderr or create.stdout).strip()[:300]}")
    url = create.stdout.strip().splitlines()[-1] if create.stdout.strip() else _existing_pr(ws, branch, gh_bin)
    return {"branch": branch, "pr_url": url, "at": now_iso()}
