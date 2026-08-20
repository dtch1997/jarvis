"""Goal-capture commit vehicle: land goal-file appends via branch + PR.

Goal bullets are the only git write mailroom performs. They used to be
in-place edits to the deployed checkout, riding to main by accident on the
memory snapshot cron's repo-wide ``git add -A`` (jarvis #47); the memory
spin-out removed that bus (jarvis #50). This module gives them the same
vehicle every other JARVIS writer uses: a worktree branch + an unlabeled PR,
which the hourly gazette sweep merges on green and the nightly version
deploy folds into the box.

Design constraints:

- **Never write to the deployed checkout.** It may be pinned/detached by a
  ``gazette version switch`` — exactly the stranding the spin-out removed.
- **Batch**: one branch/commit/PR per ``mailroom route`` run. If a previous
  run's PR is still open (the sweep hasn't come around), stack onto its
  branch — one PR accumulates until merged.
- **Fail soft, lose nothing**: any git failure before the push reports an
  error and the captures stay unrouted in the spool, retried by the next
  2-hourly run. A successful push counts as landed even if PR creation
  fails (the bullets are safe on the remote branch; the next run's close —or
  a human — ensures the PR).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import config

BRANCH = "mailroom/goal-captures"
WORKTREE_NAME = "mailroom-goal-captures"


def _env() -> dict:
    """cron gets a minimal PATH; make ~/.local/bin (gh, linked CLIs) visible."""
    env = dict(os.environ)
    local_bin = str(Path.home() / ".local" / "bin")
    if local_bin not in env.get("PATH", ""):
        env["PATH"] = f"{local_bin}:{env.get('PATH', '')}"
    return env


def _run(args: list[str], cwd: Path, timeout: int = 120) -> tuple[bool, str]:
    """(ok, combined-output-or-error). Never raises."""
    try:
        proc = subprocess.run(args, cwd=str(cwd), env=_env(),
                              capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return False, f"{args[0]}: not found"
    except subprocess.TimeoutExpired:
        return False, f"{' '.join(args[:3])}: timed out"
    out = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0:
        return False, f"{' '.join(args[:3])} failed: {out[:300]}"
    return True, out


def default_gh_pr_ensurer(repo_dir: Path, branch: str, title: str, body: str) -> tuple[str | None, str | None]:
    """Ensure an open PR exists for ``branch``; return (url, error)."""
    gh = shutil.which("gh") or (
        str(Path.home() / ".local" / "bin" / "gh")
        if (Path.home() / ".local" / "bin" / "gh").exists() else None
    )
    if gh is None:
        return None, "gh CLI not found"
    ok, out = _run([gh, "pr", "list", "--head", branch, "--state", "open",
                    "--json", "url", "-q", ".[0].url"], cwd=repo_dir)
    if ok and out.strip():
        return out.strip(), None
    ok, out = _run([gh, "pr", "create", "--head", branch, "--title", title,
                    "--body", body], cwd=repo_dir, timeout=120)
    if not ok:
        return None, out
    return out.strip().splitlines()[-1] if out.strip() else "", None


class GoalLander:
    """One route-run's goal-append landing session.

    Usage: ``goals_dir = lander.ensure_open()`` (None on failure — leave the
    capture pending), append via the returned dir, ``lander.record(goal,
    title)``, then ``pushed, pr_url, error = lander.close()``.
    """

    def __init__(self, repo_dir: Path | str | None = None,
                 goals_rel: str | None = None, pr_ensurer=default_gh_pr_ensurer):
        self.repo_dir = Path(
            repo_dir or os.environ.get("MAILROOM_GOALS_REPO") or (Path.home() / "jarvis")
        )
        self._goals_rel = goals_rel  # None = derive from config.goals_dir()
        self._pr_ensurer = pr_ensurer
        self.error: str | None = None
        self.entries: list[tuple[str, str]] = []  # (goal, title)
        self._toplevel: Path | None = None
        self._worktree: Path | None = None
        self._goals_dir: Path | None = None

    # ------------------------------------------------------------------ #
    def _fail(self, msg: str) -> None:
        self.error = msg

    def ensure_open(self) -> Path | None:
        """Create (once) the landing worktree; return its goals dir."""
        if self._goals_dir is not None:
            return self._goals_dir
        if self.error is not None:
            return None  # already failed this run; don't retry per capture
        ok, top = _run(["git", "rev-parse", "--show-toplevel"], cwd=self.repo_dir)
        if not ok:
            self._fail(top)
            return None
        self._toplevel = Path(top)
        if self._goals_rel is None:
            try:
                self._goals_rel = str(
                    Path(os.path.realpath(config.goals_dir()))
                    .relative_to(os.path.realpath(top))
                )
            except ValueError:
                self._fail(f"goals dir {config.goals_dir()} is not inside repo {top}")
                return None
        ok, msg = _run(["git", "fetch", "-q", "origin"], cwd=self._toplevel)
        if not ok:
            self._fail(msg)
            return None
        # Base on the open PR's branch if it exists remotely, else main.
        ok, _ = _run(["git", "rev-parse", "--verify", "--quiet",
                      f"origin/{BRANCH}"], cwd=self._toplevel)
        base = f"origin/{BRANCH}" if ok else "origin/main"
        worktree = self._toplevel / ".claude" / "worktrees" / WORKTREE_NAME
        # Clear leftovers from a crashed run — the branch is ours alone.
        _run(["git", "worktree", "remove", "--force", str(worktree)], cwd=self._toplevel)
        _run(["git", "branch", "-D", BRANCH], cwd=self._toplevel)
        ok, msg = _run(["git", "worktree", "add", str(worktree), "-b", BRANCH, base],
                       cwd=self._toplevel)
        if not ok:
            self._fail(msg)
            return None
        self._worktree = worktree
        self._goals_dir = worktree / self._goals_rel
        return self._goals_dir

    def record(self, goal: str, title: str) -> None:
        self.entries.append((goal, title))

    # ------------------------------------------------------------------ #
    def _cleanup(self) -> None:
        if self._toplevel is None:
            return
        if self._worktree is not None:
            _run(["git", "worktree", "remove", "--force", str(self._worktree)],
                 cwd=self._toplevel)
            self._worktree = None
        _run(["git", "branch", "-D", BRANCH], cwd=self._toplevel)
        self._goals_dir = None

    def close(self, now: datetime | None = None) -> tuple[bool, str | None, str | None]:
        """Commit + push + ensure PR. Returns (pushed, pr_url, error).

        ``pushed`` is the landing criterion: True means the bullets are safe
        on the remote branch and the captures may be marked routed.
        """
        if self._worktree is None or not self.entries:
            self._cleanup()
            return False, None, self.error
        now = now or datetime.now(timezone.utc)
        stamp = now.strftime("%Y-%m-%d %H:%M")
        lines = "\n".join(f"- {goal}: {title}" for goal, title in self.entries)
        ok, msg = _run(["git", "add", "-A", "--", self._goals_rel], cwd=self._worktree)
        if ok:
            ok, msg = _run(
                ["git", "commit", "-q", "-m",
                 f"mailroom: goal captures {stamp} ({len(self.entries)})\n\n{lines}"],
                cwd=self._worktree)
        if ok:
            ok, msg = _run(["git", "push", "-q", "-u", "origin", BRANCH],
                           cwd=self._worktree, timeout=120)
        if not ok:
            self._cleanup()
            return False, None, msg
        pr_url, pr_err = self._pr_ensurer(
            self.repo_dir, BRANCH,
            f"mailroom: goal captures {now.strftime('%Y-%m-%d')}",
            "Captured thoughts routed onto goal files by mailroom "
            "(one batched PR per route run; merges at the hourly sweep).\n\n"
            f"{lines}\n\n🤖 Opened by mailroom",
        )
        self._cleanup()
        # Pushed = landed; a PR-ensure failure is reported but not fatal
        # (bullets are safe on the remote branch; next run re-ensures).
        return True, pr_url, (f"PR ensure failed (bullets pushed): {pr_err}" if pr_err else None)
