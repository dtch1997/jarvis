"""``threads sweep`` — the auto-wrapup backstop for stale threads.

The dashboard *flags* dormancy; a flag nobody reads is not handling. This
module is the daily backstop that turns "nobody looked at this for a week"
into a classification, evidence, and a disposition. The design doc is
``jarvis-os/docs/auto-wrapup.md`` (it is the contract; this docstring only
summarizes it).

**Fully deterministic and offline — no model calls, ever.** Money is only
spent by dispatched wrap-up workers, and only in ``mode = "dispatch"``, which
starts OFF (flipping it is Daniel's call). The classification, from each
thread's latest note ``--status`` plus its observed ``status_signals``:

===========  ==========================================================
class        meaning / sweep action
===========  ==========================================================
``terminal`` done note, or the stub reads closed → skip
``blocked``  a blocked note (desk's jurisdiction) → skip
``A1``       abandoned midstream, mechanically recoverable (unpushed
             commits, or novel commits with no open PR / no parking
             note) → dispatch candidate
``A2``       abandoned midstream with a **dirty worktree** → never
             auto-touched, report-only, named explicitly
``B``        parked/ongoing and forgotten past the grace period, or
             abandoned with nothing mechanical left → a *disposition*
             proposal (resume / close / shelve-until), report-only
``fresh``    not stale, or parked within the grace period → no action
===========  ==========================================================

Two seams keep this testable and hermetic: :class:`Prober` (every ``git``/
``gh`` shell-out) and the ``submitter`` callable (the only concierge import).
``sweep --check`` swaps both, so the gate touches no network, spawns nothing
detached, and never writes to the real spool.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config

CLASSES = ("terminal", "blocked", "A1", "A2", "B", "fresh")

# note ``--status`` values that discharge a thread (``result`` is what the
# launcher's monitor writes when a full-auto executor settles).
TERMINAL_STATUS = {"done", "result"}
# ...and the ones that mean "deliberately left, not dropped".
PARKED_STATUS = {"parked", "ongoing"}

# branch names that are never a thread's own work-in-progress.
_TRUNK = {"main", "master", "HEAD", "", "develop"}
# tokens that carry no attribution signal when matching a branch to a slug.
_NOISE_TOKENS = {"pool", "main", "master", "feature", "feat", "fix", "wip",
                 "dev", "branch", "chore", "docs", "task", "work", "tmp"}
# a (repo, branch) claimed by more than this many threads is somebody's *own*
# working branch (a worker that parked notes onto many threads from one
# workspace), not each thread's work. Attributing it would be a false A1.
MAX_THREADS_PER_BRANCH = 3

# bounds, so a daily cron over ~200 threads stays cheap. Truncation is always
# reported (a silent cap reads as "covered everything" when it did not).
MAX_BRANCHES_PER_SLUG = 8
MAX_GH_CALLS = 80
# bulk-captured threads (mailroom routes dozens of thought-captures into notes
# at once) all go stale on the same day. The report keeps every one of them —
# the tail just renders as one line each instead of a full entry.
MAX_DETAILED_PER_SECTION = 25
# a wrap-up note is written *during* the session it closes, so its timestamp
# lands a moment before the session's end. Without this tolerance a proper
# park would read as "work continued after the note" and re-open the thread.
NOTE_COVERS_TOLERANCE_S = 300

DISPATCH_SPEC = """\
Run the CLAUDE.md "wrap up" procedure for thread `{slug}`.

    threads pickup {slug}

Then: push the branch, open a PR labeled with its honest lane, persist any
artifacts per the GCS convention, and finish with

    threads note {slug} --status parked|done "<state + next steps>"

Evidence the sweep gathered (this is why the thread was picked up):
{evidence}

Hard rules: never merge anything (that is gazette's job, via lanes), and never
remove a worktree you did not create. Your gate is external — {gate_name} —
and it is checked, not self-reported.
"""


# --------------------------------------------------------------------------- #
# time helpers
# --------------------------------------------------------------------------- #
def _parse_ts(value) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def _days(now: datetime, then: datetime | None) -> float | None:
    if then is None:
        return None
    return max(0.0, (now - then).total_seconds() / 86400.0)


# --------------------------------------------------------------------------- #
# the git/gh seam
# --------------------------------------------------------------------------- #
@dataclass
class BranchEvidence:
    """What is observably at risk on one ``(repo, branch)`` pair."""

    repo: str
    branch: str
    exists: bool = False
    unpushed: int = 0          # commits on the branch that no remote has
    novel: int = 0             # commits the trunk does not have
    pr: str = ""               # PR url in any state ("" = none found)
    pr_state: str = ""         # OPEN | MERGED | CLOSED
    pr_known: bool = False     # False when `gh` was unavailable/not consulted
    worktree: str = ""         # checkout path, when the branch has one
    dirty: int = 0             # uncommitted files in that worktree

    @property
    def pr_open(self) -> bool:
        return self.pr_state == "OPEN"

    @property
    def at_risk(self) -> bool:
        """Is there work here a wrap-up would actually rescue?

        A *merged* PR counts as PR'd: gazette squash-merges, so a merged branch
        keeps commits ``origin/main`` does not contain, forever. Requiring an
        **open** PR here would re-flag every merged branch on the box as
        un-PR'd work — which is exactly what the first run of this sweep did.
        """
        return bool(self.dirty or self.unpushed or (self.novel and not self.pr))

    def line(self) -> str:
        if not self.exists:
            return f"branch `{self.branch}` in `{self.repo}`: gone (no local ref)"
        bits = [f"{self.unpushed} unpushed commit(s)" if self.unpushed
                else "nothing unpushed",
                f"{self.novel} commit(s) not on trunk" if self.novel
                else "no commits off trunk"]
        if self.pr:
            bits.append(f"{self.pr_state.lower() or 'known'} PR {self.pr}")
        elif self.pr_known:
            bits.append("no PR")
        else:
            bits.append("PR state unknown (gh not consulted)")
        if self.dirty:
            bits.append(f"**{self.dirty} uncommitted file(s)** in `{self.worktree}`")
        return f"branch `{self.branch}` in `{self.repo}`: " + ", ".join(bits)


class Prober:
    """Every ``git``/``gh`` shell-out the sweep makes, in one injectable place.

    Offline in the "no model, no reasoning" sense; ``gh pr list`` is the one
    network call and it is opt-out (``gh=False``) and capped. ``--check`` and
    the tests subclass this so the gate touches no network at all.
    """

    def __init__(self, *, gh: bool = True, timeout: float = 20.0,
                 max_gh: int = MAX_GH_CALLS):
        self.gh = gh
        self.timeout = timeout
        self.max_gh = max_gh
        self.gh_calls = 0
        self.gh_truncated = 0
        self._roots: dict[str, str | None] = {}
        self._worktrees: dict[str, dict[str, tuple[str, str]]] = {}

    # ---- plumbing ----
    def run(self, args: list[str], *, cwd: str | None = None) -> tuple[int, str]:
        try:
            proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                                  timeout=self.timeout)
        except (OSError, subprocess.SubprocessError):
            return 127, ""
        return proc.returncode, (proc.stdout or "").strip()

    def repo_root(self, cwd: str) -> str | None:
        """The git top-level for a session/note cwd (``None`` if it is gone)."""
        if cwd in self._roots:
            return self._roots[cwd]
        root = None
        if cwd and Path(cwd).is_dir():
            rc, out = self.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
            root = out or None if rc == 0 else None
        self._roots[cwd] = root
        return root

    # ---- per-branch evidence ----
    def branch_state(self, repo: str, branch: str) -> BranchEvidence:
        ev = BranchEvidence(repo=repo, branch=branch)
        rc, _ = self.run(["git", "rev-parse", "--verify", "--quiet",
                          f"refs/heads/{branch}"], cwd=repo)
        if rc != 0:
            return ev
        ev.exists = True
        rc, out = self.run(["git", "rev-list", "--count", branch, "--not",
                            "--remotes"], cwd=repo)
        ev.unpushed = int(out) if rc == 0 and out.isdigit() else 0
        ev.novel = self._novel(repo, branch)
        wt = self.worktrees(repo).get(branch)
        if wt:
            ev.worktree, ev.dirty = wt[0], self._dirty(wt[0])
        ev.pr, ev.pr_state, ev.pr_known = self.pr_state(repo, branch)
        return ev

    def _novel(self, repo: str, branch: str) -> int:
        """Commits on ``branch`` that the trunk does not have."""
        for trunk in ("origin/main", "origin/master", "main", "master"):
            rc, _ = self.run(["git", "rev-parse", "--verify", "--quiet", trunk],
                             cwd=repo)
            if rc != 0:
                continue
            rc, out = self.run(["git", "rev-list", "--count", branch, "--not",
                                trunk], cwd=repo)
            if rc == 0 and out.isdigit():
                return int(out)
        return 0

    def worktrees(self, repo: str) -> dict[str, tuple[str, str]]:
        """``branch -> (path, head)`` for every checkout of this repo."""
        if repo in self._worktrees:
            return self._worktrees[repo]
        out_map: dict[str, tuple[str, str]] = {}
        rc, out = self.run(["git", "worktree", "list", "--porcelain"], cwd=repo)
        if rc == 0:
            path = head = ""
            for line in out.splitlines():
                if line.startswith("worktree "):
                    path, head = line[9:], ""
                elif line.startswith("HEAD "):
                    head = line[5:]
                elif line.startswith("branch refs/heads/"):
                    out_map[line[len("branch refs/heads/"):]] = (path, head)
        self._worktrees[repo] = out_map
        return out_map

    def _dirty(self, worktree: str) -> int:
        if not Path(worktree).is_dir():
            return 0
        rc, out = self.run(["git", "status", "--porcelain"], cwd=worktree)
        return len([ln for ln in out.splitlines() if ln.strip()]) if rc == 0 else 0

    def pr_state(self, repo: str, branch: str) -> tuple[str, str, bool]:
        """``(url, state, known)`` for the newest PR on ``branch``, any state.

        Any state, not just open: a squash-merged branch still carries commits
        the trunk does not have, so "novel commits and no *open* PR" would call
        every merged branch on the box abandoned work.
        """
        if not self.gh:
            return "", "", False
        if self.gh_calls >= self.max_gh:
            self.gh_truncated += 1
            return "", "", False
        self.gh_calls += 1
        rc, out = self.run(["gh", "pr", "list", "--head", branch, "--state",
                            "all", "--limit", "1", "--json", "url,state"],
                           cwd=repo)
        if rc != 0:
            return "", "", False
        try:
            rows = json.loads(out or "[]")
        except json.JSONDecodeError:
            return "", "", False
        if not rows:
            return "", "", True
        return str(rows[0].get("url", "")), str(rows[0].get("state", "")), True


class _NoNetworkProber(Prober):
    """``--check``'s prober: real git, ``gh`` replaced by a canned answer so the
    gate is hermetic (no network) while the PR-state logic still gets exercised."""

    def __init__(self, prs: dict | None = None, **kw):
        super().__init__(gh=False, **kw)
        self._prs = prs or {}

    def pr_state(self, repo: str, branch: str) -> tuple[str, str, bool]:
        hit = self._prs.get(branch)
        if hit is None:
            return "", "", True
        if isinstance(hit, tuple):
            return hit[0], hit[1], True
        return str(hit), "OPEN", True


# --------------------------------------------------------------------------- #
# classification
# --------------------------------------------------------------------------- #
@dataclass
class Candidate:
    slug: str
    cls: str
    last_activity: datetime | None
    stale_days: float
    reason: str
    trigger: str = ""             # why it was picked up (pre-evidence reason)
    latest: str = ""              # one-line "what this thread last was"
    note_status: str = ""
    signals: tuple[str, ...] = ()
    registered: bool = True
    branches: list[BranchEvidence] = field(default_factory=list)
    disposition: str = ""
    desk_marker: bool = False     # a BLOCKED-ON-DANIEL note already exists
    never_started: bool = False   # a captured idea: no session ever ran on it
    dispatch: dict | None = None
    dispatch_skip: str = ""

    @property
    def days(self) -> int:
        return int(self.stale_days)

    def evidence_lines(self) -> list[str]:
        return [ev.line() for ev in self.branches]


def _latest_note(thread) -> dict | None:
    return thread.notes[0] if thread.notes else None


def _latest_signals(thread) -> tuple[str, ...]:
    for rec in thread.sessions:
        sig = rec.get("status_signals") or []
        if sig:
            return tuple(str(s) for s in sig)
    return ()


def classify(thread, *, now: datetime, cfg: config.SweepConfig,
             closed: bool) -> tuple[str, str]:
    """``(class, reason)`` for one thread, before any evidence is gathered.

    ``A`` is returned as the provisional class; :func:`split_a` refines it into
    A1/A2/B once the branch evidence is in.
    """
    age = _days(now, thread.last_activity)
    if age is None:
        return "fresh", "no dated activity to age"
    if age <= cfg.stale_days:
        return "fresh", f"active {age:.0f}d ago (< {cfg.stale_days}d)"

    note = _latest_note(thread)
    status = (note or {}).get("status", "").strip().lower()
    note_ts = _parse_ts((note or {}).get("created"))
    session_ts = None
    for rec in thread.sessions:
        session_ts = _parse_ts(rec.get("t_end")) or _parse_ts(rec.get("t_start"))
        if session_ts:
            break
    # the note only speaks for the thread if nothing happened after it.
    covers = note_ts is not None and (
        session_ts is None
        or (note_ts - session_ts).total_seconds() >= -NOTE_COVERS_TOLERANCE_S)

    if closed:
        return "terminal", "the memory stub reads closed/complete"
    if covers and status in TERMINAL_STATUS:
        return "terminal", f"latest note is `{status}` ({note_ts.date()})"
    if covers and status == "blocked":
        return "blocked", f"latest note is `blocked` ({note_ts.date()})"
    if covers and status in PARKED_STATUS:
        if age > cfg.parked_grace_days:
            return "B", (f"`{status}` {age:.0f}d ago — past the "
                         f"{cfg.parked_grace_days}d grace, needs a disposition")
        return "fresh", (f"`{status}` {age:.0f}d ago — inside the "
                         f"{cfg.parked_grace_days}d grace")
    signals = _latest_signals(thread)
    if "abandoned-midstream" in signals:
        return "A", f"newest session signal is abandoned-midstream ({age:.0f}d)"
    if note is None:
        return "A", f"no note at all, {age:.0f}d since the last session"
    if not covers:
        return "A", (f"the latest note ({note_ts.date() if note_ts else '?'}) "
                     f"predates the last session — work moved on without one")
    return "A", (f"latest note carries no terminal/parked status"
                 f"{f' (`{status}`)' if status else ''}, {age:.0f}d stale")


def split_a(branches: list[BranchEvidence]) -> tuple[str, str]:
    """A → A1 / A2 / B, from the offline branch evidence."""
    dirty = [e for e in branches if e.dirty]
    if dirty:
        return "A2", ("uncommitted changes in "
                      + ", ".join(f"`{e.worktree}`" for e in dirty[:3])
                      + " — never auto-touched, a session may still be attached")
    mech = [e for e in branches if e.at_risk]
    if mech:
        return "A1", ("mechanically recoverable: "
                      + "; ".join(e.line() for e in mech[:3]))
    open_pr = [e for e in branches if e.pr_open]
    if open_pr:
        return "A1", ("PR open with no parking note: "
                      + ", ".join(e.pr for e in open_pr[:3]))
    return "B", ("abandoned midstream but nothing mechanical is at risk "
                 "(no branch with novel or unpushed commits) — it needs a "
                 "disposition, not a wrap-up")


def _disposition(cand: Candidate, *, now: datetime) -> str:
    """A drafted disposition for a B line: resume / close / shelve-until-date.

    Deterministic on purpose — one word for Daniel or the next session to act
    on, never a model's opinion.
    """
    if cand.never_started:
        return (f"**close** or shelve — captured {cand.days}d ago and never "
                "picked up (no session ran, no branch exists)")
    if cand.days > 60:
        return (f"**close** — nothing has moved in {cand.days}d; close the "
                "thread (or say shelve if it is deliberately dormant)")
    if any(e.pr_open for e in cand.branches):
        pr = next(e.pr for e in cand.branches if e.pr_open)
        return f"**resume** — an open PR is still waiting: {pr}"
    if cand.desk_marker:
        return ("**resume** — a BLOCKED-ON-DANIEL marker is stale; either "
                "re-ask or drop the blocker")
    until = (now + timedelta(days=30)).date()
    return f"**shelve-until {until}** — or resume/close if that is wrong"


# --------------------------------------------------------------------------- #
# branch discovery — which (repo, branch) pairs belong to a slug
# --------------------------------------------------------------------------- #
def _tokens(text: str) -> set[str]:
    import re
    return {t for t in re.split(r"[^a-z0-9]+", str(text).lower())
            if len(t) >= 4 and not t.isdigit() and t not in _NOISE_TOKENS}


def branch_corroborates(branch: str, slug: str) -> bool:
    """Does this branch name actually look like *this* thread's work?

    The bar exists because a note records the cwd/branch of whoever *wrote*
    it: one worker parking notes onto 166 threads from its own workspace would
    otherwise hand all 166 the same branch, and 46 bogus A1s with it. Session
    branches are exempt — weave already attributed those sessions to the
    thread; only note-captured branches have to pass here.
    """
    branch = str(branch or "")
    if branch.split("/", 1)[0] == slug:      # the launcher's <slug>/<ulid>
        return True
    return bool(_tokens(branch) & _tokens(slug))


def branch_targets(thread, *, intents: list[dict] | None = None
                   ) -> list[tuple[str, str]]:
    """``(cwd, branch)`` pairs plausibly owned by this thread, newest first.

    Sources, all already in the spool: the assigned sessions' git branch and
    recorded branch artifacts (trusted — weave attributed the session), the
    notes' captured branch+cwd (only when the branch name corroborates the
    slug — see :func:`branch_corroborates`), and the launcher's
    ``<slug>/<short-ulid>`` namespace.
    """
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(cwd, branch, *, trusted: bool):
        cwd, branch = str(cwd or "").strip(), str(branch or "").strip()
        if not cwd or branch in _TRUNK:
            return
        if not trusted and not branch_corroborates(branch, thread.slug):
            return
        key = (cwd, branch)
        if key in seen:
            return
        seen.add(key)
        out.append(key)

    for rec in thread.sessions:
        cwd = rec.get("cwd") or ""
        add(cwd, rec.get("git_branch"), trusted=True)
        for b in (rec.get("artifacts") or {}).get("branches", []) or []:
            add(cwd, b, trusted=True)
    for n in thread.notes:
        add(n.get("cwd"), n.get("branch"), trusted=False)
    for rec in intents or []:
        if rec.get("resolved_slug") != thread.slug:
            continue
        for n in thread.notes:
            add(n.get("cwd"), rec.get("branch"), trusted=True)
    return out


def _shared_branches(threads, *, intents=None) -> set[tuple[str, str]]:
    """``(cwd, branch)`` pairs too many threads claim to be anyone's own."""
    counts: dict[tuple[str, str], int] = {}
    for thread in threads:
        for key in branch_targets(thread, intents=intents):
            counts[key] = counts.get(key, 0) + 1
    return {k for k, n in counts.items() if n > MAX_THREADS_PER_BRANCH}


def gather_evidence(thread, prober: Prober, *, intents=None,
                    skip: set[tuple[str, str]] | None = None
                    ) -> tuple[list[BranchEvidence], int]:
    """Branch evidence for one thread, plus the number of targets skipped."""
    targets = [t for t in branch_targets(thread, intents=intents)
               if not skip or t not in skip]
    dropped = max(0, len(targets) - MAX_BRANCHES_PER_SLUG)
    evidence: list[BranchEvidence] = []
    done: set[tuple[str, str]] = set()
    for cwd, branch in targets[:MAX_BRANCHES_PER_SLUG]:
        root = prober.repo_root(cwd)
        if not root or (root, branch) in done:
            continue
        done.add((root, branch))
        evidence.append(prober.branch_state(root, branch))
    return [e for e in evidence if e.exists], dropped


# --------------------------------------------------------------------------- #
# sweep state — dispatch bookkeeping (cooldowns, pending tasks)
# --------------------------------------------------------------------------- #
def load_state() -> dict:
    path = config.sweep_state_path()
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {"dispatches": {}}
    if not isinstance(data, dict):
        return {"dispatches": {}}
    data.setdefault("dispatches", {})
    return data


def write_state(state: dict) -> None:
    config.sweep_dir().mkdir(parents=True, exist_ok=True)
    config.sweep_state_path().write_text(json.dumps(state, indent=2))


_PENDING_TASK = {"queued", "running", "waiting", "blocked", "new", "pending"}


def dispatch_block(slug: str, state: dict, *, now: datetime,
                   cfg: config.SweepConfig) -> str:
    """Why ``slug`` must not be dispatched right now ("" = it may be)."""
    history = (state.get("dispatches") or {}).get(slug) or []
    if not history:
        return ""
    last = history[-1]
    from . import launch
    task = launch.read_task(str(last.get("task_id") or "")) or {}
    status = str(task.get("status") or "").lower()
    at = _parse_ts(last.get("at"))
    age = _days(now, at)
    if not task or status in _PENDING_TASK:
        return f"a dispatch is pending (task `{last.get('task_id')}`)"
    if status not in ("done",) and age is not None and age < cfg.cooldown_days:
        return (f"last dispatch `{last.get('task_id')}` ended `{status or '?'}` "
                f"{age:.0f}d ago — inside the {cfg.cooldown_days}d cooldown")
    if status not in ("done",):
        return ""
    if age is not None and age < cfg.cooldown_days:
        return (f"dispatched {age:.0f}d ago (task `{last.get('task_id')}` done) "
                f"— inside the {cfg.cooldown_days}d cooldown")
    return ""


def default_submitter(*, spec: str, title: str, repo: str, branch: str,
                      gate_cmd: str, pr_gate: bool, budget_usd: float) -> str:
    """Submit one wrap-up task to the concierge pool; return its task id.

    The only concierge import in this module, and the only place the sweep
    spends money. ``THREADS_DISABLE_ENQUEUE=1`` hard-refuses — the same seam
    the offline gates use to prove nothing escapes a fixture spool.
    """
    if os.environ.get("THREADS_DISABLE_ENQUEUE"):
        raise RuntimeError("dispatch refused: THREADS_DISABLE_ENQUEUE is set")
    from concierge.api import Pool
    from concierge.gates import PrOpen, ShellOk
    gate = ShellOk(gate_cmd)
    if pr_gate:
        gate = PrOpen() & gate
    return Pool(home=config.concierge_home()).submit(
        spec, title=title, repo=Path(repo), branch=branch, gate=gate,
        budget_usd=budget_usd)


def gate_name(slug: str, *, pr_gate: bool) -> str:
    cmd = f"threads sweep --verify {slug}"
    return (f"PrOpen() & ShellOk('{cmd}')" if pr_gate else f"ShellOk('{cmd}')")


# --------------------------------------------------------------------------- #
# the sweep itself
# --------------------------------------------------------------------------- #
@dataclass
class SweepResult:
    generated_at: datetime
    mode: str
    threads: int
    counts: dict[str, int]
    candidates: list[Candidate]
    exempt: list[str] = field(default_factory=list)
    report_path: Path | None = None
    report_text: str = ""
    dispatched: list[dict] = field(default_factory=list)
    flared: bool = False
    truncated: list[str] = field(default_factory=list)

    @property
    def actionable(self) -> list[Candidate]:
        return [c for c in self.candidates if c.cls in ("A1", "A2", "B")]

    def headline(self) -> str:
        c = self.counts
        return (f"{self.threads} thread(s): {c.get('A1', 0)} A1 · "
                f"{c.get('A2', 0)} A2 · {c.get('B', 0)} B · "
                f"{c.get('blocked', 0)} blocked · {c.get('terminal', 0)} terminal "
                f"· {c.get('fresh', 0)} fresh")

    def report(self) -> str:
        lines = [f"sweep {self.mode}: {self.headline()}"]
        for cand in self.actionable:
            lines.append(f"  {cand.cls:<2} {cand.slug} ({cand.days}d) — "
                         f"{cand.reason}")
        if self.report_path:
            lines.append(f"  report → {self.report_path}")
        for t in self.truncated:
            lines.append(f"  ! {t}")
        return "\n".join(lines)


def sweep(*, now: datetime | None = None, cfg: config.Config | None = None,
          prober: Prober | None = None, submitter=default_submitter,
          write: bool = True, flare_info: bool = True,
          mode: str | None = None, budget_usd: float | None = None
          ) -> SweepResult:
    """Classify every thread, gather A-evidence, report (and maybe dispatch).

    Never writes a note onto a thread — that would reset the very staleness
    clock this measures. ``write=False`` makes the whole run read-only (what
    ``--dry-run`` and the offline gate use).
    """
    from . import dashboard
    now = now or datetime.now(timezone.utc)
    cfg = cfg or config.load_config()
    scfg = cfg.sweep
    if mode:
        scfg = replace(scfg, mode=mode)
    prober = prober if prober is not None else Prober()

    dash = dashboard.build(now=now, cfg=cfg, sweep=False)
    try:
        from . import launch
        intents = launch.load_intents()
    except Exception:  # noqa: BLE001 — an unreadable launcher spool is not fatal
        intents = []

    exempt = set(scfg.exempt)
    counts = {k: 0 for k in CLASSES}
    candidates: list[Candidate] = []
    truncated: list[str] = []
    skipped_targets = 0
    shared = _shared_branches(dash.threads, intents=intents)

    for thread in sorted(dash.threads, key=lambda t: t.slug):
        if thread.slug in exempt:
            continue
        cls, reason = classify(thread, now=now, cfg=scfg, closed=thread.closed)
        note = _latest_note(thread) or {}
        cand = Candidate(
            slug=thread.slug, cls=cls, last_activity=thread.last_activity,
            stale_days=_days(now, thread.last_activity) or 0.0, reason=reason,
            latest=(note.get("title") or thread.latest_title or "")[:120],
            note_status=str(note.get("status") or ""),
            signals=_latest_signals(thread), registered=thread.registered,
            desk_marker=any("BLOCKED-ON-DANIEL" in (n.get("body") or "")
                            for n in thread.notes[:3]),
            never_started=not thread.sessions,
        )
        if cls == "A":
            cand.branches, dropped = gather_evidence(thread, prober,
                                                     intents=intents,
                                                     skip=shared)
            skipped_targets += dropped
            cand.trigger = reason
            cand.cls, cand.reason = split_a(cand.branches)
        if cand.cls == "B":
            if cand.never_started and not cand.branches:
                cand.reason = (f"captured {cand.days}d ago and never picked up "
                               "— it needs a disposition, not a wrap-up")
            cand.disposition = _disposition(cand, now=now)
        counts[cand.cls] = counts.get(cand.cls, 0) + 1
        candidates.append(cand)

    if shared:
        truncated.append(f"{len(shared)} branch(es) claimed by more than "
                         f"{MAX_THREADS_PER_BRANCH} threads were ignored as "
                         "somebody's own working branch: "
                         + ", ".join(f"`{b}`" for _c, b in sorted(shared)[:5]))
    if skipped_targets:
        truncated.append(f"{skipped_targets} branch target(s) beyond the "
                         f"{MAX_BRANCHES_PER_SLUG}/thread cap were not probed")
    if prober.gh_truncated:
        truncated.append(f"{prober.gh_truncated} PR lookup(s) skipped — the "
                         f"{prober.max_gh}-call `gh` cap was hit this run")

    result = SweepResult(generated_at=now, mode=scfg.mode, threads=len(candidates),
                         counts=counts, candidates=candidates,
                         exempt=sorted(exempt), truncated=truncated)

    if scfg.mode == "dispatch":
        _dispatch(result, cfg=scfg, now=now, submitter=submitter, write=write,
                  budget_usd=budget_usd)

    result.report_text = render_report(result)
    if write:
        _persist(result, flare_info=flare_info)
    return result


def _dispatch(result: SweepResult, *, cfg: config.SweepConfig, now: datetime,
              submitter, write: bool, budget_usd: float | None) -> None:
    """Submit up to ``max_dispatch_per_run`` A1 wrap-ups, under the cooldowns."""
    state = load_state() if write else {"dispatches": {}}
    sent = 0
    for cand in result.candidates:
        if cand.cls != "A1":
            continue
        if sent >= cfg.max_dispatch_per_run:
            cand.dispatch_skip = (f"per-run cap of {cfg.max_dispatch_per_run} "
                                  "dispatch(es) reached")
            continue
        block = dispatch_block(cand.slug, state, now=now, cfg=cfg)
        if block:
            cand.dispatch_skip = block
            continue
        pr_gate = any(e.novel and not e.pr for e in cand.branches)
        name = gate_name(cand.slug, pr_gate=pr_gate)
        repo = cand.branches[0].repo if cand.branches else ""
        branch = cand.branches[0].branch if cand.branches else ""
        spec = DISPATCH_SPEC.format(
            slug=cand.slug, gate_name=name,
            evidence="\n".join(f"- {ln}" for ln in cand.evidence_lines()) or
                     "- (no branch evidence)")
        try:
            tid = submitter(spec=spec, title=f"thread wrap-up: {cand.slug}",
                            repo=repo, branch=branch,
                            gate_cmd=f"threads sweep --verify {cand.slug}",
                            pr_gate=pr_gate,
                            budget_usd=budget_usd if budget_usd is not None
                            else float(os.environ.get(
                                "THREADS_SWEEP_BUDGET_USD", "10")))
        except Exception as exc:  # noqa: BLE001 — a refusal is a report line
            cand.dispatch_skip = f"dispatch failed: {type(exc).__name__}: {exc}"
            cand.reason += "  BLOCKED-ON-DANIEL: sweep could not dispatch it"
            continue
        rec = {"slug": cand.slug, "task_id": tid, "at": now.isoformat(),
               "gate": name}
        cand.dispatch = rec
        result.dispatched.append(rec)
        state.setdefault("dispatches", {}).setdefault(cand.slug, []).append(rec)
        sent += 1
    if write and result.dispatched:
        state["last_dispatch_run"] = now.isoformat()
        write_state(state)


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #
_SECTIONS = (
    ("A1", "A1 — abandoned midstream, mechanically recoverable",
     "A worker can finish these safely: push the branch, open the PR, park the "
     "note. In report mode they are proposals, nothing was touched."),
    ("A2", "A2 — abandoned midstream with a dirty worktree (never auto-touched)",
     "A session may still be attached; committing someone's mid-edit state is "
     "how you corrupt work. These are yours, always."),
    ("B", "B — parked and forgotten (disposition needed)",
     "Nothing is at risk; the thread needs a call. Each line carries a drafted "
     "disposition — one word settles it."),
)


def render_report(result: SweepResult) -> str:
    """The daily markdown report. Day-resolution timestamps and integer day
    counts on purpose: two runs on the same unchanged spool are byte-identical,
    which is what makes "an immediate re-run is a no-op" checkable."""
    r = result
    out = [f"# threads sweep — {r.generated_at.date()}", "",
           f"_Deterministic and offline (zero model calls). Mode: **{r.mode}**._",
           "", f"**{r.headline()}**", ""]
    if r.exempt:
        out += [f"Exempt (never swept): {', '.join(r.exempt)}", ""]
    for cls, title, blurb in _SECTIONS:
        rows = sorted((c for c in r.candidates if c.cls == cls),
                      key=lambda c: -c.stale_days)
        if not rows:
            continue
        out += [f"## {title} ({len(rows)})", "", blurb, ""]
        for cand in rows[:MAX_DETAILED_PER_SECTION]:
            out += _render_candidate(cand)
        tail = rows[MAX_DETAILED_PER_SECTION:]
        if tail:
            out += [f"<details><summary>{len(tail)} more {cls} thread(s), one "
                    "line each</summary>", ""]
            out += [f"- `{c.slug}` ({c.days}d): {c.disposition or c.reason}"
                    for c in tail]
            out += ["", "</details>", ""]
    blocked = sorted((c for c in r.candidates if c.cls == "blocked"),
                     key=lambda c: -c.stale_days)
    if blocked:
        out += ["## blocked — desk's jurisdiction (skipped here)", ""]
        for cand in blocked:
            marker = "" if cand.desk_marker else \
                " — no BLOCKED-ON-DANIEL marker, so desk may not see it"
            out.append(f"- `{cand.slug}` ({cand.days}d): {cand.reason}{marker}")
        out.append("")
    if r.dispatched:
        out += ["## dispatched this run", ""]
        for rec in r.dispatched:
            out.append(f"- `{rec['slug']}` → concierge `{rec['task_id']}`, "
                       f"gate {rec['gate']}")
        out.append("")
    if r.truncated:
        out += ["## coverage caps hit this run", ""]
        out += [f"- {t}" for t in r.truncated] + [""]
    out += ["---", "",
            f"terminal: {r.counts.get('terminal', 0)} · "
            f"fresh (incl. parked inside the grace): {r.counts.get('fresh', 0)}",
            ""]
    return "\n".join(out)


def _render_candidate(cand: Candidate) -> list[str]:
    reg = "" if cand.registered else " _(unregistered — note-seeded thread)_"
    out = [f"### `{cand.slug}` — stale {cand.days}d{reg}", "",
           f"- why: {cand.reason}"]
    if cand.trigger:
        out.append(f"- picked up because: {cand.trigger}")
    if cand.latest:
        status = f" (note `{cand.note_status}`)" if cand.note_status else ""
        out.append(f"- last: {cand.latest}{status}")
    if cand.signals:
        out.append(f"- newest observed signal(s): {', '.join(cand.signals)}")
    out += [f"- {ln}" for ln in cand.evidence_lines()]
    if cand.cls in ("A1", "A2") and not cand.branches:
        out.append("- no live branch found for this thread (context only)")
    if cand.disposition:
        out.append(f"- disposition: {cand.disposition}")
    if cand.dispatch:
        out.append(f"- dispatched: concierge `{cand.dispatch['task_id']}` "
                   f"(gate {cand.dispatch['gate']})")
    elif cand.dispatch_skip:
        out.append(f"- not dispatched: {cand.dispatch_skip}")
    elif cand.cls == "A1":
        pr_gate = any(e.novel and not e.pr for e in cand.branches)
        out.append("- wrap-up gate if dispatched: "
                   f"{gate_name(cand.slug, pr_gate=pr_gate)}")
    out.append("")
    return out


def _persist(result: SweepResult, *, flare_info: bool) -> None:
    """Append the log line (always), write the report + flare (when there is
    something to say). One flare per run, never one per thread."""
    config.sweep_dir().mkdir(parents=True, exist_ok=True)
    if result.actionable or result.dispatched:
        path = config.sweep_dir() / f"{result.generated_at.date()}.md"
        path.write_text(result.report_text)
        result.report_path = path
        if flare_info:
            result.flared = _flare(result)
    row = {"at": result.generated_at.isoformat(timespec="seconds"),
           "mode": result.mode, "threads": result.threads,
           "counts": result.counts,
           "dispatched": [d["task_id"] for d in result.dispatched],
           "report": str(result.report_path) if result.report_path else None,
           "truncated": result.truncated}
    with config.sweep_log_path().open("a") as f:
        f.write(json.dumps(row) + "\n")


def _flare(result: SweepResult) -> bool:
    c = result.counts
    msg = (f"threads sweep: {c.get('A1', 0)} A1 (mechanical), "
           f"{c.get('A2', 0)} A2 (dirty worktree), {c.get('B', 0)} B "
           f"(disposition) out of {result.threads} threads")
    if result.dispatched:
        msg += f" — dispatched {len(result.dispatched)} wrap-up(s)"
    msg += f" — {result.report_path}"
    try:
        subprocess.run(["flare", msg, "--sev", "info"], timeout=15,
                       capture_output=True)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


# --------------------------------------------------------------------------- #
# ``threads sweep --verify <slug>`` — the concierge gate
# --------------------------------------------------------------------------- #
def verify(slug: str, *, now: datetime | None = None, prober: Prober | None = None,
           since: datetime | None = None) -> tuple[bool, str]:
    """Is thread ``slug`` actually wrapped up?

    Exits 0 iff (1) it has a wrap-up note (`parked`/`done`) newer than the
    dispatch time, (2) none of its branches have unpushed commits, and (3)
    every branch with novel commits has a PR. An already-*merged* PR satisfies
    (3): the worker is forbidden from merging, so a merged branch means
    gazette got there first — success, not stranded work. External and
    unfakeable by the worker, which is why it can gate a dispatch.
    """
    from . import dashboard
    now = now or datetime.now(timezone.utc)
    prober = prober if prober is not None else Prober()
    slug = slug.strip().lower()

    if since is None:
        history = (load_state().get("dispatches") or {}).get(slug) or []
        since = _parse_ts(history[-1].get("at")) if history else None
    dash = dashboard.build(now=now, sweep=False)
    thread = next((t for t in dash.threads if t.slug == slug), None)
    if thread is None:
        return False, (f"verify {slug}: FAIL — no such thread in the spool "
                       "(no notes, no assigned sessions)")
    if since is None:
        # no dispatch on record: the bar is a wrap-up note newer than the last
        # observed session, i.e. the work was parked *after* it was worked on.
        for rec in thread.sessions:
            since = _parse_ts(rec.get("t_end")) or _parse_ts(rec.get("t_start"))
            if since:
                break

    lines, ok = [], True
    wrap = None
    for n in thread.notes:
        ts = _parse_ts(n.get("created"))
        status = str(n.get("status") or "").lower()
        if status in TERMINAL_STATUS | {"parked"} and (
                since is None or (ts is not None and ts > since)):
            wrap = n
            break
    if wrap is None:
        ok = False
        lines.append(f"  FAIL  a `parked`/`done` note newer than "
                     f"{since.isoformat() if since else 'the last session'}")
    else:
        lines.append(f"  PASS  wrap-up note `{wrap.get('status')}` at "
                     f"{wrap.get('created')} — {wrap.get('title', '')[:60]}")

    evidence, dropped = gather_evidence(thread, prober)
    if dropped:
        lines.append(f"  note  {dropped} branch target(s) beyond the cap "
                     "were not probed")
    for ev in evidence:
        if ev.unpushed:
            ok = False
            lines.append(f"  FAIL  {ev.line()}")
        elif ev.novel and not ev.pr:
            ok = False
            lines.append(f"  FAIL  {ev.line()} (novel commits need a PR)")
        else:
            lines.append(f"  PASS  {ev.line()}")
    if not evidence:
        lines.append("  PASS  no live branch carries work for this thread")
    header = f"verify {slug}: {'OK' if ok else 'FAIL'}"
    return ok, "\n".join([header, *lines])


# --------------------------------------------------------------------------- #
# ``threads sweep --check`` — the offline gate
# --------------------------------------------------------------------------- #
class _ModelCallForbidden(RuntimeError):
    pass


def _no_model_runner(*_a, **_k):
    raise _ModelCallForbidden("the sweep made a model call (it must be offline)")


class _Checks:
    """A tiny assertion recorder, so the gate reports *what* it verified."""

    def __init__(self):
        self.lines: list[str] = []
        self.failures = 0

    def ok(self, condition, label: str, detail: str = "") -> bool:
        good = bool(condition)
        if not good:
            self.failures += 1
        one_line = " · ".join(str(detail).split("\n"))[:160]
        self.lines.append(f"  {'PASS' if good else 'FAIL'}  {label}"
                          + (f" — {one_line}" if one_line else ""))
        return good

    def section(self, title: str) -> None:
        self.lines.append(title)


def _listing(d: Path) -> list[str]:
    if not d.is_dir():
        return []
    return sorted(f"{p.relative_to(d)}:{p.stat().st_mtime_ns}"
                  for p in d.rglob("*") if p.is_file())


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                   text=True)


def _fixture_repo(root: Path) -> Path:
    """A real git repo with a trunk and a remote, so the git plumbing under
    test is the real thing (no network: the 'remote' is a bare repo on disk)."""
    remote = root / "remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True,
                   capture_output=True)
    repo = root / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "sweep@check.invalid")
    _git(repo, "config", "user.name", "sweep check")
    (repo / "README.md").write_text("# fixture\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "trunk")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "origin", "main")
    return repo


def _fixture_branch(repo: Path, branch: str, *, commits: int = 1,
                    push: bool = False) -> None:
    _git(repo, "checkout", "-q", "-b", branch, "main")
    for i in range(commits):
        (repo / f"{branch.replace('/', '-')}-{i}.txt").write_text(f"work {i}\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", f"{branch} work {i}")
    if push:
        _git(repo, "push", "-q", "origin", branch)
    _git(repo, "checkout", "-q", "main")


def _fixture_thread(slug: str, *, days_ago: float, status: str = "",
                    cwd: str = "", branch: str = "", body: str = "body",
                    now: datetime, signals: tuple[str, ...] = (),
                    session_days_ago: float | None = None) -> None:
    """One thread in the fixture spool: a note and/or an observed session."""
    from . import note, spool
    if status or body:
        note.add_note(slug, body, title=f"{slug} note", status=status or None,
                      cwd=cwd or "/nonexistent", branch=branch,
                      now=now - timedelta(days=days_ago))
    if session_days_ago is not None:
        ts = now - timedelta(days=session_days_ago)
        sid = f"sess-{slug}"
        spool.write_summary({
            "session_id": sid, "cwd": cwd or "/nonexistent",
            "git_branch": branch or "main",
            "t_start": (ts - timedelta(hours=1)).isoformat(),
            "t_end": ts.isoformat(), "n_messages": 20, "transcript_size": 100,
            "trivial": False, "is_concierge": False,
            "hints": {"stubs": [], "goals": [], "repos": [], "branches": [],
                      "prs": []},
            "method": "model", "model": "m", "cost_usd": 0.0,
            "title": f"{slug} session", "summary": "s",
            "artifacts": {"branches": [], "prs": [], "files": [], "urls": []},
            "status_signals": list(signals) or ["ongoing"],
            "candidate_slugs": [], "keywords": [],
            "generated_at": ts.isoformat(),
        })
        spool.write_assignments(spool.load_assignments() +
                                [{"session_id": sid, "slug": slug,
                                  "method": "fixture", "confidence": 1.0}])


def _check_fixtures(c: _Checks, root: Path, now: datetime) -> None:
    repo = _fixture_repo(root)
    # A1: committed but never pushed.
    _fixture_branch(repo, "a1-thread/work", commits=2)
    # A1-pr: pushed, PR open, but no parking note.
    _fixture_branch(repo, "a1-pr-thread/work", commits=1, push=True)
    # A2: a dirty worktree the sweep does not own.
    _fixture_branch(repo, "a2-thread/work", commits=1, push=True)
    wt = root / "wt-a2"
    _git(repo, "worktree", "add", "-q", str(wt), "a2-thread/work")
    (wt / "half-edited.py").write_text("x = 1  # mid-edit\n")

    r = str(repo)
    # A candidates: the newest state is a *session*, not a note.
    _fixture_thread("a1-thread", days_ago=0, body="", cwd=r,
                    branch="a1-thread/work", now=now, session_days_ago=20,
                    signals=("abandoned-midstream",))
    _fixture_thread("a1-pr-thread", days_ago=0, body="", cwd=r,
                    branch="a1-pr-thread/work", now=now, session_days_ago=15)
    _fixture_thread("a2-thread", days_ago=0, body="", cwd=r,
                    branch="a2-thread/work", now=now, session_days_ago=30)
    _fixture_thread("b-thread", days_ago=45, status="parked", cwd=r, now=now)
    _fixture_thread("b-ongoing-thread", days_ago=40, status="ongoing", cwd=r,
                    now=now)
    _fixture_thread("b-grace-thread", days_ago=12, status="parked", cwd=r, now=now)
    _fixture_thread("terminal-thread", days_ago=40, status="done", cwd=r, now=now)
    _fixture_thread("blocked-thread", days_ago=40, status="blocked", cwd=r,
                    body="BLOCKED-ON-DANIEL: which bucket?", now=now)
    _fixture_thread("fresh-thread", days_ago=1, status="ongoing", cwd=r, now=now)
    # a wrap-up note written moments before its session ended still counts as
    # covering it (the note is the last word, not the transcript's clock).
    _fixture_thread("parked-at-the-buzzer", days_ago=30.0001, status="parked",
                    cwd=r, now=now, session_days_ago=30)

    prober = _NoNetworkProber({"a1-pr-thread/work": "https://x.invalid/pr/9",
                               "a2-thread/work": "https://x.invalid/pr/8"})
    cfg = config.load_config()
    res = sweep(now=now, cfg=cfg, prober=prober, write=True, flare_info=False)
    by = {cand.slug: cand for cand in res.candidates}

    c.section("classification (fixture threads, one per class):")
    for slug, want in (("a1-thread", "A1"), ("a1-pr-thread", "A1"),
                       ("a2-thread", "A2"), ("b-thread", "B"),
                       ("b-ongoing-thread", "B"), ("b-grace-thread", "fresh"),
                       ("terminal-thread", "terminal"),
                       ("blocked-thread", "blocked"), ("fresh-thread", "fresh"),
                       ("parked-at-the-buzzer", "B")):
        got = by.get(slug).cls if slug in by else "MISSING"
        c.ok(got == want, f"{slug} → {want}", f"got {got}")
    c.ok(sum(res.counts.values()) == res.threads and
         all(k in CLASSES for k in res.counts),
         "every thread lands in exactly one of terminal/blocked/A1/A2/B/fresh",
         f"{res.counts}")

    c.section("evidence in the report (branch, unpushed count, PR state):")
    text = res.report_text
    c.ok("2 unpushed commit(s)" in text, "A1 shows its unpushed commit count")
    c.ok("a1-thread/work" in text, "A1 names the branch")
    c.ok("https://x.invalid/pr/9" in text, "an open PR is shown when one exists")
    c.ok("no PR" in text, "a branch with no PR says so")
    c.ok("uncommitted file(s)" in text and "wt-a2" in text,
         "A2 names the dirty worktree explicitly")
    c.ok(by["b-thread"].disposition.startswith("**shelve-until")
         or "close" in by["b-thread"].disposition,
         "a B line carries a drafted disposition",
         by["b-thread"].disposition)
    c.ok(res.report_path and res.report_path.exists(), "the report file is written")
    c.ok(config.sweep_log_path().exists(), "the run appended a log line")

    c.section("idempotence (an immediate re-run is a no-op):")
    before = res.report_path.read_text()
    lines_before = len(config.sweep_log_path().read_text().splitlines())
    notes_before = _listing(config.notes_dir())
    res2 = sweep(now=now + timedelta(minutes=3), cfg=cfg,
                 prober=_NoNetworkProber({"a1-pr-thread/work": "https://x.invalid/pr/9",
                                          "a2-thread/work": "https://x.invalid/pr/8"}),
                 write=True, flare_info=False)
    c.ok(res2.report_path.read_text() == before,
         "the re-run rewrites a byte-identical report")
    c.ok(len(config.sweep_log_path().read_text().splitlines()) == lines_before + 1,
         "and appends exactly one more log line (idle runs are logged too)")
    c.ok(_listing(config.notes_dir()) == notes_before,
         "the sweep writes no notes onto threads (it never resets the clock)")

    c.section("dispatch mode (config-gated; caps, cooldown, A2/B never sent):")
    sent: list[dict] = []

    def fake_submit(**kw):
        sent.append(kw)
        return f"t-fake-{len(sent)}"

    dcfg = replace(cfg, sweep=replace(cfg.sweep, mode="dispatch",
                                      max_dispatch_per_run=1))
    res3 = sweep(now=now, cfg=dcfg, prober=_NoNetworkProber(), write=True,
                 flare_info=False, submitter=fake_submit)
    c.ok(len(sent) == 1, "the per-run dispatch cap is a hard cap", f"{len(sent)} sent")
    c.ok(all("thread wrap-up" in k["title"] for k in sent),
         "the dispatched task is a wrap-up task")
    c.ok(sent and sent[0]["gate_cmd"].startswith("threads sweep --verify"),
         "the dispatch is gated on `threads sweep --verify <slug>`",
         sent[0]["gate_cmd"] if sent else "")
    c.ok(sent and sent[0]["pr_gate"] is True,
         "a branch with novel commits adds PrOpen() to the gate")
    c.ok("never merge anything" in (sent[0]["spec"] if sent else ""),
         "the spec forbids merging (that is gazette's job)")
    dispatched_slugs = {d["slug"] for d in res3.dispatched}
    c.ok(not (dispatched_slugs & {"a2-thread", "b-thread", "blocked-thread",
                                  "terminal-thread"}),
         "A2 / B / blocked / terminal are never dispatched",
         f"{sorted(dispatched_slugs)}")
    # the pending task blocks a re-dispatch even before any cooldown elapses
    res4 = sweep(now=now + timedelta(minutes=5), cfg=dcfg,
                 prober=_NoNetworkProber(), write=True, flare_info=False,
                 submitter=fake_submit)
    redis = {d["slug"] for d in res4.dispatched}
    c.ok(not (redis & dispatched_slugs),
         "a slug with a pending dispatch is not re-dispatched", f"{sorted(redis)}")
    prior = os.environ.get("THREADS_DISABLE_ENQUEUE")
    os.environ["THREADS_DISABLE_ENQUEUE"] = "1"
    try:
        raised = False
        try:
            default_submitter(spec="x", title="t", repo=str(repo), branch="main",
                              gate_cmd="true", pr_gate=False, budget_usd=1.0)
        except RuntimeError:
            raised = True
        c.ok(raised, "the real submitter hard-refuses under THREADS_DISABLE_ENQUEUE")
    finally:
        if prior is None:
            os.environ.pop("THREADS_DISABLE_ENQUEUE", None)
        else:
            os.environ["THREADS_DISABLE_ENQUEUE"] = prior

    c.section("--verify on a wrapped and an unwrapped fixture:")
    pv = _NoNetworkProber({"a1-pr-thread/work": "https://x.invalid/pr/9"})
    unwrapped_ok, unwrapped_txt = verify("a1-thread", now=now, prober=pv,
                                         since=now - timedelta(days=25))
    c.ok(not unwrapped_ok, "an unwrapped A1 thread fails the gate")
    c.ok("unpushed" in unwrapped_txt,
         "and the failure names the unpushed commits", unwrapped_txt.strip()[:90])
    # now actually wrap it up: push the branch, open (fake) the PR, park a note
    _git(repo, "push", "-q", "origin", "a1-thread/work")
    from . import note as note_mod
    note_mod.add_note("a1-thread", "Pushed, PR open, parking.",
                      title="wrapped up", status="parked", cwd=str(repo),
                      branch="a1-thread/work", now=now)
    pw = _NoNetworkProber({"a1-thread/work": "https://x.invalid/pr/7"})
    wrapped_ok, wrapped_txt = verify("a1-thread", now=now + timedelta(minutes=1),
                                     prober=pw, since=now - timedelta(days=25))
    c.ok(wrapped_ok, "the same thread passes once wrapped up", wrapped_txt)
    missing_ok, _ = verify("no-such-thread-anywhere", now=now, prober=pw)
    c.ok(not missing_ok, "verify fails closed on an unknown slug")
    # a pushed branch with novel commits but no PR must still fail
    _fixture_thread("nopr-thread", days_ago=0.1, status="parked", cwd=str(repo),
                    branch="a1-pr-thread/work", now=now)
    nopr_ok, nopr_txt = verify("nopr-thread", now=now + timedelta(minutes=1),
                               prober=_NoNetworkProber(), since=now - timedelta(days=1))
    c.ok(not nopr_ok and "need a PR" in nopr_txt,
         "a parked thread whose novel commits were never PR'd still fails")


def sweep_check() -> tuple[bool, str]:
    """Offline gate: classify the real spool read-only, then assert the whole
    contract against fixtures in a throwaway spool.

    Hermetic by construction — model calls raise, ``gh`` is never invoked,
    ``THREADS_DISABLE_ENQUEUE`` is set so no detached process or concierge
    submission can escape the fixture spool, and the real ``~/.threads`` is
    byte-compared before and after.
    """
    import tempfile

    from . import summarize

    c = _Checks()
    now = datetime.now(timezone.utc)
    real_runner, summarize.default_runner = summarize.default_runner, _no_model_runner
    try:
        # ---- half 1: the real spool, read-only, no subprocesses at all ----
        c.section(f"real spool ({config.threads_dir()}), read-only:")
        before = _listing(config.sweep_dir())
        try:
            res = sweep(now=now, prober=_NoNetworkProber(), write=False,
                        flare_info=False)
            c.ok(res.threads > 0, "every registered thread is classified",
                 f"{res.threads} thread(s): {res.counts}")
            c.ok(sum(res.counts.values()) == res.threads,
                 "the classes partition the threads (no thread counted twice)",
                 f"{res.counts}")
            c.ok(all(cand.cls in CLASSES for cand in res.candidates),
                 "every class is one of terminal/blocked/A1/A2/B/fresh")
            c.ok(len(res.report_text) > 200, "the real report renders",
                 f"{len(res.report_text)} bytes")
            c.ok(res.report_path is None,
                 "a --check run writes no report file to the real spool")
        except _ModelCallForbidden as exc:
            c.ok(False, "zero model calls in the sweep", str(exc))
        except Exception as exc:  # noqa: BLE001
            import traceback
            c.ok(False, "the real spool classifies",
                 f"{type(exc).__name__}: {exc}\n"
                 + "".join(traceback.format_exc()[-1200:]))
        c.ok(_listing(config.sweep_dir()) == before,
             "the real sweep spool is untouched by --check")
        c.ok(True, "zero model calls (the summarizer runner is stubbed to raise)")

        # ---- half 2: fixtures, in a throwaway spool ----
        saved = {k: os.environ.get(k)
                 for k in ("THREADS_HOME", "THREADS_CONCIERGE_HOME",
                           "THREADS_MEMORY_DIR", "THREADS_PROJECTS_DIR",
                           "THREADS_GOALS_DIR", "THREADS_DISABLE_ENQUEUE")}
        with tempfile.TemporaryDirectory(prefix="threads-sweep-check-") as tmp:
            root = Path(tmp)
            for name, key in (("home", "THREADS_HOME"),
                              ("concierge-home", "THREADS_CONCIERGE_HOME"),
                              ("memory", "THREADS_MEMORY_DIR"),
                              ("projects", "THREADS_PROJECTS_DIR"),
                              ("goals", "THREADS_GOALS_DIR")):
                (root / name).mkdir(parents=True, exist_ok=True)
                os.environ[key] = str(root / name)
            # nothing detached, nothing submitted: a process spawned here would
            # inherit these temp paths and fail loudly once the dir is gone.
            os.environ["THREADS_DISABLE_ENQUEUE"] = "1"
            config.ensure_spool()
            try:
                _check_fixtures(c, root, now)
            except Exception as exc:  # noqa: BLE001 — a crash is a gate failure
                import traceback
                c.ok(False, "fixture checks completed",
                     f"{type(exc).__name__}: {exc}\n"
                     + "".join(traceback.format_exc()[-1500:]))
            finally:
                for key, value in saved.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
    finally:
        summarize.default_runner = real_runner

    ok = c.failures == 0
    n = sum(1 for ln in c.lines if ln.startswith("  "))
    header = f"sweep --check {'OK' if ok else 'FAIL'} — {n} assertion(s), {c.failures} failed"
    return ok, "\n".join([header, *c.lines])
