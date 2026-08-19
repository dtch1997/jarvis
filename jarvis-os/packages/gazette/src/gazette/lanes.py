"""Lane resolution and merge decisions — pure functions, no I/O.

Two lanes (2026-08-19 rework — Daniel's call: merge-on-green + nightly
versions replace the delay window):

- **auto** — the default. No label needed; merges as soon as checks are
  green. Post-merge safety is versioning (``gazette version switch``), not a
  veto window.
- **requires-approval** — money, credentials, external-facing actions,
  destructive ops. Never cron-merged; waits for Daniel via desk/flare.

A PR's lane comes from its label (``requires-approval``; legacy
``lane:blocked`` is an alias, legacy ``lane:delay`` is retired and treated
as auto with an anomaly note), then gets demoted by what it touches: any PR
touching credential-like paths becomes requires-approval regardless of
label. Behavior-shaping paths (CLAUDE.md, ops/**, …) no longer demote —
they only annotate the decision so the sweep log and morning edition can
call the merge out.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import PurePosixPath

from .config import Config

LABEL_AUTO = "lane:auto"  # optional; same as unlabeled
LABEL_DELAY = "lane:delay"  # retired 2026-08-19; treated as auto
LABEL_APPROVAL = "requires-approval"
LABEL_BLOCKED = "lane:blocked"  # legacy alias for requires-approval
LABEL_VETO = "veto"

# Labels the coverage search scans for in unswept repos — includes the legacy
# names so a straggler PR opened under the old convention still shows up.
LANE_LABELS = (LABEL_APPROVAL, LABEL_AUTO, LABEL_DELAY, LABEL_BLOCKED)


class Lane(str, Enum):
    AUTO = "auto"
    APPROVAL = "requires-approval"


@dataclass
class PR:
    """Normalized view of an open PR (see gh.list_open_prs)."""

    repo: str
    number: int
    title: str
    url: str
    author: str
    created_at: datetime
    is_draft: bool = False
    labels: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    checks: str = "none"  # none | passing | pending | failing
    review_decision: str = ""  # "" | APPROVED | CHANGES_REQUESTED | REVIEW_REQUIRED
    head_ref: str = ""
    cross_repo: bool = False

    @property
    def ref(self) -> str:
        return f"{self.repo.split('/')[-1]}#{self.number}"


def path_matches(path: str, glob: str) -> bool:
    """fnmatch with two conveniences: ``dir/**`` matches everything under dir,
    and a bare filename glob (no ``/``) matches at any depth (so ``CLAUDE.md``
    protects nested copies too)."""
    if glob.endswith("/**"):
        prefix = glob[:-2]  # keep trailing slash
        return path == glob[:-3] or path.startswith(prefix)
    if fnmatch.fnmatch(path, glob):
        return True
    if glob.startswith("**/") and fnmatch.fnmatch(path, glob[3:]):
        return True  # "**/x" also means a top-level "x"
    if "/" not in glob:
        return fnmatch.fnmatch(PurePosixPath(path).name, glob)
    return False


def _touched(files: list[str], globs: list[str]) -> list[str]:
    return [f for f in files if any(path_matches(f, g) for g in globs)]


def resolve_lane(labels: list[str], files: list[str], cfg: Config) -> tuple[Lane, list[str]]:
    """Return (lane, reasons). Reasons record demotions/legacy labels for the notes."""
    reasons: list[str] = []
    hot = _touched(files, cfg.blocked_globs)
    if hot:
        if LABEL_APPROVAL not in labels and LABEL_BLOCKED not in labels:
            reasons.append(
                f"demoted to requires-approval: touches {', '.join(hot[:3])}"
            )
        return Lane.APPROVAL, reasons
    if LABEL_APPROVAL in labels or LABEL_BLOCKED in labels:
        return Lane.APPROVAL, reasons
    if LABEL_DELAY in labels:
        reasons.append(
            "carries retired lane:delay — delay lane removed 2026-08-19, treating as auto"
        )
    return Lane.AUTO, reasons


@dataclass
class Decision:
    action: str  # merge | wait | skip
    lane: Lane
    reason: str
    anomalies: list[str] = field(default_factory=list)


def decide(pr: PR, cfg: Config, now: datetime) -> Decision:
    """The sweep's whole policy, as one pure function over a normalized PR."""
    lane, reasons = resolve_lane(pr.labels, pr.files, cfg)
    anomalies = list(reasons)
    if pr.is_draft:
        return Decision("skip", lane, "draft", anomalies)
    if LABEL_VETO in pr.labels:
        return Decision("skip", lane, "vetoed (`veto` label)", anomalies)
    if pr.review_decision == "CHANGES_REQUESTED":
        return Decision("skip", lane, "vetoed (changes requested)", anomalies)
    if lane is Lane.APPROVAL:
        return Decision("skip", lane, "requires approval — waits for Daniel", anomalies)
    if pr.checks == "failing":
        anomalies.append("checks failing")
        return Decision("wait", lane, "checks failing", anomalies)
    if pr.checks == "pending":
        return Decision("wait", lane, "checks pending", anomalies)
    # Behavior-shaping paths merge like anything else now (versioning is the
    # backstop), but the merge is annotated so it stands out in the sweep log
    # and the morning edition's news.
    shaping = _touched(pr.files, cfg.protected_globs)
    if shaping:
        return Decision(
            "merge", lane,
            f"checks green (behavior-shaping: touches {', '.join(shaping[:3])})",
            anomalies,
        )
    return Decision("merge", lane, "checks green", anomalies)
