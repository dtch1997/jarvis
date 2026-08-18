"""Thin wrappers around the ``gh`` CLI. All network I/O lives here so the
policy (lanes.py), sweep, and notes stay pure and offline-testable. Every
function degrades gracefully: a missing ``gh`` or an API error yields empty
data plus a human-readable warning — never an exception."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import Config, coverage_owners
from .lanes import LANE_LABELS, PR

_PR_FIELDS = (
    "number,title,url,author,createdAt,isDraft,labels,files,"
    "reviewDecision,statusCheckRollup,headRefName,isCrossRepository"
)


def _gh_bin() -> str | None:
    """Resolve the ``gh`` executable. cron gets a minimal PATH, so fall back to
    ``~/.local/bin`` (where ops/link-clis.sh puts the agent CLIs) before giving
    up — this is the belt-and-braces to the cron PATH fix in ops/cron.tab."""
    exe = shutil.which("gh")
    if exe:
        return exe
    candidate = Path.home() / ".local" / "bin" / "gh"
    return str(candidate) if candidate.exists() else None


def _gh(args: list[str], timeout: int = 60) -> tuple[str, str | None]:
    """Run gh, return (stdout, warning)."""
    exe = _gh_bin()
    if exe is None:
        return "", f"gh CLI not found (searched PATH: {os.environ.get('PATH', '')})"
    try:
        proc = subprocess.run(
            [exe, *args], capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        return "", "gh CLI not found"
    except subprocess.TimeoutExpired:
        return "", f"gh timed out: {' '.join(args[:4])}"
    if proc.returncode != 0:
        return "", f"gh failed ({' '.join(args[:4])}): {proc.stderr.strip()[:200]}"
    return proc.stdout, None


def _parse_ts(value: str) -> datetime:
    ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def _norm_checks(rollup) -> str:
    if not rollup:
        return "none"
    states = {
        (c.get("conclusion") or c.get("state") or "").upper() for c in rollup
    }
    if states & {"FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED"}:
        return "failing"
    if states & {"", "PENDING", "IN_PROGRESS", "QUEUED", "EXPECTED", "WAITING"}:
        return "pending"
    return "passing"


def list_open_prs(repo: str) -> tuple[list[PR], list[str], bool]:
    """Return (prs, warnings, failed). ``failed`` is True when the collector
    itself could not reach GitHub (gh missing, nonzero exit, timeout, or
    unparseable output) — an incomplete result, not a genuine empty repo — so
    callers can promote it to an anomaly instead of a silent quiet day. Soft
    per-row parse issues stay in ``warnings`` with ``failed=False``."""
    out, warn = _gh(
        ["pr", "list", "-R", repo, "--state", "open", "--limit", "100",
         "--json", _PR_FIELDS]
    )
    if warn:
        return [], [f"{repo}: {warn}"], True
    warnings: list[str] = []
    prs: list[PR] = []
    try:
        rows = json.loads(out)
    except json.JSONDecodeError as e:
        return [], [f"{repo}: bad gh output ({e})"], True
    for row in rows:
        try:
            pr = PR(
                repo=repo,
                number=row["number"],
                title=row.get("title", ""),
                url=row.get("url", ""),
                author=(row.get("author") or {}).get("login", ""),
                created_at=_parse_ts(row["createdAt"]),
                is_draft=bool(row.get("isDraft")),
                labels=[l["name"] for l in row.get("labels") or []],
                files=[f["path"] for f in row.get("files") or []],
                checks=_norm_checks(row.get("statusCheckRollup")),
                review_decision=row.get("reviewDecision") or "",
                head_ref=row.get("headRefName", ""),
                cross_repo=bool(row.get("isCrossRepository")),
            )
        except (KeyError, ValueError) as e:
            warnings.append(f"{repo}: could not parse PR row ({e})")
            continue
        prs.append(pr)
    return prs, warnings, False


def list_merged_since(repo: str, since: datetime) -> tuple[list[dict], list[str], bool]:
    """Return (merged, warnings, failed). See ``list_open_prs`` for ``failed``."""
    out, warn = _gh(
        ["pr", "list", "-R", repo, "--state", "merged", "--limit", "50",
         "--search", f"merged:>={since.date().isoformat()}",
         "--json", "number,title,url,mergedAt,author,labels"]
    )
    if warn:
        return [], [f"{repo}: {warn}"], True
    try:
        rows = json.loads(out)
    except json.JSONDecodeError as e:
        return [], [f"{repo}: bad gh output ({e})"], True
    merged = []
    for row in rows:
        ts = _parse_ts(row["mergedAt"])
        if ts < since:
            continue  # search granularity is per-day; trim to the window
        merged.append({
            "repo": repo,
            "number": row["number"],
            "title": row.get("title", ""),
            "url": row.get("url", ""),
            "merged_at": ts,
            "author": (row.get("author") or {}).get("login", ""),
            "labels": [l["name"] for l in row.get("labels") or []],
        })
    return merged, [], False


def search_lane_prs(owner: str, label: str) -> tuple[list[dict], str | None]:
    """Open PRs under ``owner`` carrying ``label``, across every repo.

    Repo-agnostic on purpose: this is how the sweep learns about PRs that opted
    into the lane convention in a repo it was never told to sweep. Returns
    (rows, warning); a warning means the search could not be trusted.
    """
    out, warn = _gh(
        ["search", "prs", "--owner", owner, "--state", "open", "--label", label,
         "--limit", "100", "--json", "repository,number,title,url,isDraft"]
    )
    if warn:
        return [], f"lane-coverage search ({owner}, {label}): {warn}"
    try:
        rows = json.loads(out)
    except json.JSONDecodeError as e:
        return [], f"lane-coverage search ({owner}, {label}): bad gh output ({e})"
    return [
        {
            "repo": (row.get("repository") or {}).get("nameWithOwner", ""),
            "number": row.get("number"),
            "title": row.get("title", ""),
            "url": row.get("url", ""),
            "label": label,
            "is_draft": bool(row.get("isDraft")),
        }
        for row in rows
    ], None


def unswept_lane_prs(cfg: Config) -> tuple[list[dict], list[str]]:
    """Lane-labelled open PRs living in repos ``cfg.github_repos`` does not cover.

    These are the silent ones: the sweep never enumerates them, so they earn no
    skip/wait/merge row and no collector warning — they simply never appear.
    Returns (rows, warnings); each row is one stranded PR.
    """
    swept = {r.lower() for r in cfg.github_repos}
    rows: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, int]] = set()
    for owner in coverage_owners(cfg):
        for label in LANE_LABELS:
            found, warn = search_lane_prs(owner, label)
            if warn:
                warnings.append(warn)
                continue
            for row in found:
                repo = row["repo"]
                if not repo or repo.lower() in swept:
                    continue
                key = (repo.lower(), row["number"])
                if key in seen:
                    continue
                seen.add(key)
                rows.append(row)
    return rows, warnings


def coverage_gap_messages(rows: list[dict]) -> list[str]:
    """Render ``unswept_lane_prs`` rows as edition/report lines."""
    return [
        f"{r['repo'].split('/')[-1]}#{r['number']} carries {r['label']} but "
        f"{r['repo']} is not in github_repos — no sweep will ever decide it "
        f"({r['title'][:60]}) — {r['url']}"
        for r in rows
    ]


def merge_pr(pr: PR) -> str | None:
    """Squash-merge; returns a warning string on failure, None on success.

    Deliberately no ``--delete-branch`` (pinned-main convention: it half-fails
    when the branch is checked out in a worktree); the remote branch is deleted
    via the API instead, and local worktree cleanup stays with sessions.
    """
    _, warn = _gh(["pr", "merge", "-R", pr.repo, str(pr.number), "--squash"], timeout=120)
    if warn:
        return f"{pr.ref}: merge failed — {warn}"
    if pr.head_ref and not pr.cross_repo:
        _, del_warn = _gh(["api", "-X", "DELETE", f"repos/{pr.repo}/git/refs/heads/{pr.head_ref}"])
        if del_warn:
            return f"{pr.ref}: merged, but remote branch delete failed — {del_warn}"
    return None
