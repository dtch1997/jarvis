"""gazette config: ``~/.config/gazette/config.toml``, created on first run with
the defaults written as comments so a human can see (and edit) what is in
effect."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# Post-cutover repo set (2026-08-18): the jarvis monorepo plus the sibling
# repos whose crons open lane-labelled PRs. Keep this in sync with the live
# ~/.config/gazette/config.toml — a repo missing from BOTH is a PR nobody
# sweeps (that is how ArcadiaImpact/jarvis#152 and life-theses#11 were
# stranded; ``watch_owners`` now makes the gap loud instead of silent).
DEFAULTS = {
    "github_repos": ["dtch1997/jarvis", "dtch1997/life-theses"],
    # Owners scanned for lane-labelled PRs in repos NOT in github_repos, so a
    # repo that opts into the lane convention without being swept shows up as
    # an anomaly. Empty = derive from github_repos' owners.
    "watch_owners": [],
    # Behavior-shaping paths: merges touching these are ANNOTATED (sweep log +
    # edition), never held back — versioning is the rollback, not a delay.
    # Both bare and monorepo-prefixed paths: the sweep spans the monorepo and
    # single-project sibling repos, and a bare filename glob matches at any
    # depth (see lanes.path_matches).
    "protected_globs": [
        "CLAUDE.md",
        "HOUSE_RULES.md",
        "ops/**",
        "jarvis-os/ops/**",
        ".claude/**",
        "jarvis-os/.claude/**",
        "goals/README.md",
        "jarvis-os/goals/README.md",
        "jarvis-os/packages/**",
        "jarvis-tools/packages/**",
    ],
    # Credential-like paths: any PR touching these is requires-approval
    # regardless of label — the one demotion that survived the 2026-08-19
    # lane rework.
    "blocked_globs": [
        "**/.env*",
        "**/*secret*",
        "**/*credential*",
    ],
    "notes_window_hours": 24,
    "synthesis_cmd": "claude -p --model sonnet",
    # The deployed checkout `gazette version` operates on (a symlink into the
    # monorepo is fine; git resolves the toplevel itself).
    "checkout": "~/jarvis",
    # Post-deploy steps, run at the git toplevel after every deploy/switch so
    # the venv, PATH links, and crontab always match the deployed tree.
    "deploy_cmds": [
        "uv sync --all-packages -q",
        "jarvis-tools/ops/link-clis.sh",
        "jarvis-os/ops/install-cron.sh",
    ],
}

_TEMPLATE = """\
# gazette config — consumer-mode PR flow (merge sweep + patch notes + versions).
# Uncomment and edit any key to override its default (shown below).

# github_repos = ["dtch1997/jarvis", "dtch1997/life-theses"]
# watch_owners = []           # owners scanned for lane-labelled PRs in unswept repos ([] = owners of github_repos)
# protected_globs = ["CLAUDE.md", "HOUSE_RULES.md", "ops/**", "jarvis-os/ops/**", ".claude/**", "jarvis-os/.claude/**", "goals/README.md", "jarvis-os/goals/README.md", "jarvis-os/packages/**", "jarvis-tools/packages/**"]
# blocked_globs = ["**/.env*", "**/*secret*", "**/*credential*"]
# notes_window_hours = 24
# synthesis_cmd = "claude -p --model sonnet"   # "" disables the LLM news pass
# checkout = "~/jarvis"       # the deployed checkout `gazette version` manages
# deploy_cmds = ["uv sync --all-packages -q", "jarvis-tools/ops/link-clis.sh", "jarvis-os/ops/install-cron.sh"]
"""


@dataclass
class Config:
    github_repos: list[str] = field(default_factory=lambda: list(DEFAULTS["github_repos"]))
    watch_owners: list[str] = field(default_factory=lambda: list(DEFAULTS["watch_owners"]))
    protected_globs: list[str] = field(default_factory=lambda: list(DEFAULTS["protected_globs"]))
    blocked_globs: list[str] = field(default_factory=lambda: list(DEFAULTS["blocked_globs"]))
    notes_window_hours: int = DEFAULTS["notes_window_hours"]
    synthesis_cmd: str = DEFAULTS["synthesis_cmd"]
    checkout: str = DEFAULTS["checkout"]
    deploy_cmds: list[str] = field(default_factory=lambda: list(DEFAULTS["deploy_cmds"]))


def coverage_owners(cfg: "Config") -> list[str]:
    """Owners to scan for lane-labelled PRs outside ``github_repos``.

    Defaults to the owners of the swept repos: repointing the sweep at a new
    repo then leaves the old sibling repos under the same owner still watched,
    which is exactly the migration case that stranded PRs on 2026-08-18.
    """
    if cfg.watch_owners:
        return list(dict.fromkeys(cfg.watch_owners))
    return list(dict.fromkeys(r.split("/")[0] for r in cfg.github_repos if "/" in r))


def _home() -> Path:
    return Path(os.environ.get("GAZETTE_HOME") or Path.home())


def config_path() -> Path:
    override = os.environ.get("GAZETTE_CONFIG")
    return Path(override) if override else _home() / ".config" / "gazette" / "config.toml"


def spool_dir() -> Path:
    return _home() / ".gazette"


def load_config() -> Config:
    """Load config, creating the commented-defaults template on first run.

    Unknown keys are ignored, so a config.toml written for the old lane model
    (delay_hours, delay_editions) still loads cleanly after the 2026-08-19
    rework — the retired knobs just stop meaning anything.
    """
    path = config_path()
    if not path.exists():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_TEMPLATE)
        except OSError:
            pass
        return Config()
    try:
        data = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        data = {}
    merged = {**DEFAULTS, **{k: v for k, v in data.items() if k in DEFAULTS}}
    return Config(
        github_repos=list(merged["github_repos"]),
        watch_owners=list(merged["watch_owners"]),
        protected_globs=list(merged["protected_globs"]),
        blocked_globs=list(merged["blocked_globs"]),
        notes_window_hours=int(merged["notes_window_hours"]),
        synthesis_cmd=str(merged["synthesis_cmd"]),
        checkout=str(merged["checkout"]),
        deploy_cmds=list(merged["deploy_cmds"]),
    )
