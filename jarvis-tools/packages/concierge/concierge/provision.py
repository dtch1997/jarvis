"""Workspace provisioning helpers — make a freshly-created workspace safe.

Concierge workspaces are bare clones (or bare `mkdir`s); unlike the jarvis
checkout they carry no Claude Code hooks. Workers have repeatedly launched GPU
pipelines as `nohup … &` inside `run_in_background` Bash calls, orphaning the
real job. `install_guard_hook` drops the same PreToolUse(Bash) guard the jarvis
repo uses into every workspace and registers it in the workspace's Claude
settings, merging (never clobbering) a cloned repo's own settings and keeping
the additions out of worker PRs.

`validate_repo` is the other half: a submit-time shape check on the thing the
workspace will be cloned FROM, so an uncloneable value fails at the callsite
instead of inside the daemon (issue #33).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"
GUARD_ASSET = ASSETS / "guard_background_tasks.py"

# Relative to the workspace root. The hook command references the copied script
# via $CLAUDE_PROJECT_DIR (set by Claude Code to the project/workspace root when
# it runs hooks), so it stays valid regardless of the absolute workspace path.
_HOOK_REL = ".claude/hooks/guard_background_tasks.py"
_SETTINGS_REL = ".claude/settings.json"
_HOOK_COMMAND = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/guard_background_tasks.py"'
_HOOK_ENTRY = {
    "type": "command",
    "command": _HOOK_COMMAND,
    "timeout": 10,
    "statusMessage": "Checking background-task safety",
}



# -- what the workspace is cloned from ------------------------------------- #

# A cloneable repo spec: a git transport URL, an scp-style ssh spec, or a local
# path. A bare `owner/repo` slug is NOT a git remote — `git clone
# dtch1997/jarvis` exits 128, and until issue #33 that surfaced as a dead
# daemon rather than a failed task.
_URL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://\S+$")          # https://host/p, file:///p
_SCP_RE = re.compile(r"^[^\s/@:]+@[^\s/@:]+:\S+$")                  # git@github.com:o/r.git
_HOST_RE = re.compile(r"^[A-Za-z0-9._\-]+\.[A-Za-z0-9._\-]+:\S+$")   # github.com:o/r.git
_SLUG_RE = re.compile(r"^[\w.\-]+/[\w.\-]+$")                       # owner/repo (rejected)


def validate_repo(repo) -> str:
    """Return `repo` as a git-cloneable string, or raise ValueError.

    Shape check only — it never touches the network, so a typo'd host or a
    private repo still fails at clone time (which now fails that task, not the
    daemon). What it catches is the class of value git rejects outright: a bare
    GitHub slug, a project name, a sentence. Existing local paths come back
    absolute, since the daemon clones from its own cwd, not the submitter's.
    """
    spec = str(repo).strip()
    if not spec:
        raise ValueError("repo must be a non-empty git URL, ssh spec, or local path")
    if _URL_RE.match(spec) or _SCP_RE.match(spec) or _HOST_RE.match(spec):
        return spec
    path = Path(spec).expanduser()
    # path-shaped but absent is accepted: git reports a missing directory
    # clearly, and that now fails the task rather than the daemon
    if path.exists() or spec.startswith(("/", "./", "../", "~")):
        return os.path.abspath(str(path))
    hint = ""
    if _SLUG_RE.match(spec):
        owner, name = spec.split("/")
        hint = (f" — that looks like a GitHub slug; pass "
                f"'git@github.com:{owner}/{name}.git' or "
                f"'https://github.com/{owner}/{name}.git'")
    raise ValueError(
        f"repo={spec!r} is not cloneable{hint}. Pass a git URL (https://…, "
        "ssh://…, git://…, file://…), an ssh spec (git@host:owner/repo.git), "
        "or a local path (/abs/path, ./rel).")


def install_guard_hook(ws: Path) -> None:
    """Copy the background-task guard into the workspace and register it as a
    PreToolUse(Bash) hook. Idempotent; safe on both the clone and mkdir paths."""
    ws = Path(ws)
    hook_dst = ws / _HOOK_REL
    hook_dst.parent.mkdir(parents=True, exist_ok=True)
    hook_dst.write_text(GUARD_ASSET.read_text())
    hook_dst.chmod(0o755)

    settings_path = ws / _SETTINGS_REL
    settings, settings_tracked = {}, False
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except (json.JSONDecodeError, OSError):
            settings = {}
        settings_tracked = _git_tracked(ws, _SETTINGS_REL)
    if not isinstance(settings, dict):
        settings = {}
    _merge_bash_hook(settings)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")

    # Keep our additions out of worker PRs: exclude untracked files, and
    # skip-worktree a settings.json the target repo already tracks.
    if (ws / ".git").exists():
        _git_exclude(ws, [_HOOK_REL] + ([] if settings_tracked else [_SETTINGS_REL]))
        if settings_tracked:
            subprocess.run(["git", "-C", str(ws), "update-index", "--skip-worktree", _SETTINGS_REL],
                           check=False, capture_output=True)


_AGENTS_REL = "AGENTS.md"
_HOUSE_MARKER = "<!-- concierge:house-rules -->"


def install_house_rules(ws: Path, home_root: Path) -> None:
    """Append the pool's HOUSE_RULES.md to the workspace `AGENTS.md` — the Codex
    analogue of the Claude backend's system-prompt append. Kept out of worker
    PRs exactly like the guard hook: `.git/info/exclude` when AGENTS.md is
    untracked, `skip-worktree` when the target repo already tracks it. Idempotent
    (a marker guards re-appends), and a no-op when no HOUSE_RULES.md exists."""
    ws, home_root = Path(ws), Path(home_root)
    rules = home_root / "HOUSE_RULES.md"
    if not rules.exists():
        return
    target = ws / _AGENTS_REL
    if target.exists() and _HOUSE_MARKER in target.read_text(errors="replace"):
        return  # already installed this attempt/session
    was_tracked = target.exists() and (ws / ".git").exists() and _git_tracked(ws, _AGENTS_REL)
    block = f"\n\n{_HOUSE_MARKER}\n# Pool house rules\n\n{rules.read_text()}\n"
    with target.open("a") as f:
        f.write(block)

    if (ws / ".git").exists():
        _git_exclude(ws, [] if was_tracked else [_AGENTS_REL])
        if was_tracked:
            subprocess.run(["git", "-C", str(ws), "update-index", "--skip-worktree", _AGENTS_REL],
                           check=False, capture_output=True)


def _merge_bash_hook(settings: dict) -> None:
    """Add the guard to settings['hooks']['PreToolUse'] under the Bash matcher,
    preserving any hooks the target repo already declares. Idempotent."""
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = settings["hooks"] = {}
    pre = hooks.setdefault("PreToolUse", [])
    if not isinstance(pre, list):
        pre = hooks["PreToolUse"] = []
    for group in pre:
        if isinstance(group, dict) and group.get("matcher") == "Bash":
            group_hooks = group.setdefault("hooks", [])
            if not isinstance(group_hooks, list):
                group_hooks = group["hooks"] = []
            if any(isinstance(h, dict) and h.get("command") == _HOOK_COMMAND for h in group_hooks):
                return
            group_hooks.append(dict(_HOOK_ENTRY))
            return
    pre.append({"matcher": "Bash", "hooks": [dict(_HOOK_ENTRY)]})


def _git_tracked(ws: Path, rel: str) -> bool:
    r = subprocess.run(["git", "-C", str(ws), "ls-files", "--error-unmatch", rel],
                       capture_output=True, text=True)
    return r.returncode == 0


def _git_exclude(ws: Path, rels: list[str]) -> None:
    exclude = ws / ".git" / "info" / "exclude"
    if not exclude.parent.exists():
        return
    existing = exclude.read_text().splitlines() if exclude.exists() else []
    have = set(existing)
    add = [r for r in rels if r not in have]
    if not add:
        return
    lines = existing + ["# concierge: workspace guard hook (do not commit)"] + add
    exclude.write_text("\n".join(lines) + "\n")
