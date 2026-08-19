"""``threads launch`` — the intent → thread front door.

Today the rest of this package is *observational* (scan reconstructs threads
after the fact). The launcher is the other direction: a thread exists **first**,
as a declared intent, and work accrues to it.

The send contract is deliberately tiny. :func:`accept` does exactly one
synchronous thing — persist a durable, ULID-keyed intent record to the spool —
and returns a receipt in well under 100ms with **no model call and no network**.
Everything after that (routing to a slug, spawning an executor) is asynchronous
and lands *on the thread*, never back at the sender; failures become thread
notes + warning flares, never silence.

The design doc is ``jarvis-os/docs/thread-launcher.md``.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import config, note, registry, summarize

# terminal notes that discharge the termination contract.
TERMINAL = {"result", "blocked", "failed"}

# a non-spawned intent younger than this is treated as legitimately in-flight by
# the consistency gate (routing/spawning is async), not as an inconsistency.
INFLIGHT_GRACE_SECONDS = 600

# Goal-cell provenance (see ``set_goal``): the router drafts, Daniel edits.
GOAL_PENDING, GOAL_DRAFTED, GOAL_EDITED = "pending", "drafted", "edited"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _ulid() -> str:
    """Dependency-free, monotonic-sortable, Crockford-base32 ULID."""
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    value = (int(time.time() * 1000) << 80) | secrets.randbits(80)
    chars = []
    for _ in range(26):
        chars.append(alphabet[value & 31])
        value >>= 5
    return "".join(reversed(chars))


def _short(intent_id: str) -> str:
    """The short-ULID used in branch names (``<slug>/<short-ulid>``)."""
    return intent_id[-8:].lower()


def _offline_runner(*_a, **_k) -> dict:
    """A router runner that makes no call — used by --dry-run and --check."""
    return {"text": "{}", "cost_usd": 0.0}


# --------------------------------------------------------------------------- #
# intent spool I/O (atomic writes; one JSON file per ULID)
# --------------------------------------------------------------------------- #
def _path(intent_id: str) -> Path:
    return config.intents_dir() / f"{intent_id}.json"


def _write(rec: dict) -> None:
    config.ensure_spool()
    path = _path(rec["id"])
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, indent=2) + "\n")
    os.replace(tmp, path)


def load_intent(intent_id: str) -> dict:
    return json.loads(_path(intent_id).read_text())


def load_intents() -> list[dict]:
    d = config.intents_dir()
    if not d.is_dir():
        return []
    out = []
    for path in sorted(d.glob("*.json"), reverse=True):
        try:
            out.append(json.loads(path.read_text()))
        except (OSError, json.JSONDecodeError):
            continue
    return out


def _remove_intent(intent_id: str) -> None:
    try:
        _path(intent_id).unlink()
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# the synchronous accept step — durable, no model, no network
# --------------------------------------------------------------------------- #
def accept(text: str, *, mode: str = "full-auto", slug: str | None = None,
           dry_run: bool = False, enqueue: bool = True) -> dict:
    """Persist an intent record and return the receipt. Target: <100ms.

    ``enqueue`` fires the detached router/executor (skipped for --dry-run and
    the offline gate). It never blocks the accept: routing and spawning happen
    in a separate process and write onto the thread.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("intent text is empty")
    if mode not in ("full-auto", "copilot"):
        raise ValueError("mode must be 'full-auto' or 'copilot'")
    rec = {
        "id": _ulid(),
        "text": text,
        "mode": mode,
        "requested_slug": slug.strip().lower() if slug else None,
        "created_at": _now(),
        "updated_at": _now(),
        "state": "accepted",
        "resolved_slug": None,
        "route": None,
        "executor_handle": None,
        "terminal_state": None,
        "dry_run": bool(dry_run),
        # the board's Goal column. The literal gate is derived here — the menu
        # is a regex over the intent text, so it stays inside the accept budget
        # (no model, no network); the prose is drafted async by the router.
        "goal": None,
        "goal_state": GOAL_PENDING,
        "goal_history": [],
        "gate": gate_spec(None, text),
    }
    _write(rec)
    if enqueue:
        enqueue_intent(rec["id"])
    return rec


def enqueue_intent(intent_id: str) -> None:
    """Spawn the detached router/executor process for one intent.

    ``THREADS_DISABLE_ENQUEUE=1`` makes this a no-op — the seam the offline
    gates (``board --check``) use to exercise the real ``POST /launch`` handler
    without routing a synthetic intent or spawning an executor.
    """
    if os.environ.get("THREADS_DISABLE_ENQUEUE"):
        return
    subprocess.Popen(
        [sys.executable, "-m", "threads.launch", "--process", intent_id],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True, env={**os.environ},
    )


# --------------------------------------------------------------------------- #
# router — slug resolution (one cheap model call, deterministic fallbacks)
# --------------------------------------------------------------------------- #
def _slugify(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())[:7]
    return "-".join(words)[:60] or f"thread-{_ulid()[-6:].lower()}"


def _route(rec: dict, *, runner=summarize.default_runner
           ) -> tuple[str, str, str, str]:
    """Return ``(slug, route_method, interpretation, drafted_goal)``.

    Priority: pinned slug → one model match against the registry (accept only
    an existing slug) → mint a candidate slug from the intent text. The same
    call drafts the Goal cell (deliverables + exit criteria); a pinned slug or
    an unusable response falls back to :func:`fallback_goal`, so the Goal is
    always populated even with no model available.
    """
    gate = gate_spec_for(rec)
    requested = rec.get("requested_slug")
    if requested:
        return (requested, "pinned",
                "Pinned by the sender; proceeding with the stated intent.",
                fallback_goal(rec["text"], gate))
    reg = registry.load_registry()
    index = registry.memory_index_slugs()
    prompt = (
        "Route one intent to an existing thread and state its goal. Return "
        'ONLY JSON: {"slug": string|null, "reading": string, "assumptions": '
        'string, "deliverables": string, "exit_criteria": string}. '
        "slug must be one exact registry slug below, or null if none fits. "
        "deliverables = the artifact(s) that will exist; exit_criteria = the "
        "externally checkable condition that means done (this gate will be "
        f"checked as: {gate['name']}).\n"
        "REGISTRY (slug: description):\n- " + "\n- ".join(index)
        + "\n\nINTENT:\n" + rec["text"] + "\n")
    try:
        result = runner(prompt, model=config.MODEL)
        data = json.loads(summarize._strip_fence(result.get("text", "")))
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    proposed = data.get("slug")
    if isinstance(proposed, str) and reg.has(proposed):
        slug, route = proposed, "model-match"
    else:
        slug, route = _slugify(rec["text"]), "minted"
    reading = str(data.get("reading") or rec["text"])
    assumptions = str(data.get("assumptions") or "no extra assumptions")
    deliverables = str(data.get("deliverables") or "").strip()
    exit_criteria = str(data.get("exit_criteria") or "").strip()
    if deliverables and exit_criteria:
        goal = f"Deliverables: {deliverables}\n\nDone when: {exit_criteria}"
    else:
        goal = fallback_goal(rec["text"], gate)
    return slug, route, f"{reading}\n\nAssumptions: {assumptions}", goal


# --------------------------------------------------------------------------- #
# the gate menu — pure, offline, and re-derivable from an edited Goal
# --------------------------------------------------------------------------- #
# Full-auto gate menu (documented in the package README). The router picks one
# from this small menu; it is externally checked, never worker self-report.
# these match as prefixes ("test" catches "tests", "build" catches "building")
_REPO_WORDS = ("code", "implement", "fix", "build", "commit", "refactor",
               "patch", "test", "ship", "merge", "file")
# "pr" has to match as a whole word: as a prefix it fires on "improve",
# "approach", "practice", … and silently gates a write-up on an open PR.
_PR_WORD = re.compile(r"\bprs?\b")
# a concrete results artifact named in the goal makes the work compute-shaped:
# a PR alone would let a placeholder settle (house rules: results, not
# artifacts), so the gate composes an assertion on the file.
_RESULTS_FILE = re.compile(r"\b[\w./-]+\.(?:jsonl|csv|parquet)\b")
RESULT_FILE = ".threads-result.md"


def gate_spec(goal: str | None, text: str) -> dict:
    """The machine-readable gate for one intent, as ``{name, kind, arg}``.

    Pure and offline — a regex over prose, no model and no concierge import, so
    it is safe inside the accept budget and inside the offline gates. The
    **goal wins when present**: that is what makes the Goal cell the veto
    surface (an edit that re-specs the work re-derives the gate), and why the
    intent text is only the fallback for a not-yet-drafted goal.
    """
    basis = (goal or "").strip() or text
    low = basis.lower()
    repo_shaped = bool(_PR_WORD.search(low)) or any(w in low for w in _REPO_WORDS)
    results = _RESULTS_FILE.search(basis)
    if repo_shaped and results:
        cmd = f"test -s {results.group(0)}"
        return {"kind": "pr_open_and_shell_ok", "arg": cmd,
                "name": f"PrOpen() & ShellOk('{cmd}') [compute-shaped work]"}
    if repo_shaped:
        return {"kind": "pr_open", "arg": None,
                "name": "PrOpen() [repo-shaped work]"}
    cmd = f"test -s {RESULT_FILE}"
    return {"kind": "shell_ok", "arg": cmd,
            "name": f"ShellOk('{cmd}') [question-shaped work]"}


def gate_spec_for(rec: dict) -> dict:
    """The gate stored on an intent record, derived on demand for old records."""
    spec = rec.get("gate")
    if isinstance(spec, dict) and spec.get("kind"):
        return spec
    return gate_spec(rec.get("goal"), rec.get("text") or "")


def gate_object(spec: dict):
    """Build the concierge gate object for a spec (the only concierge import)."""
    from concierge.gates import PrOpen, ShellOk
    kind, arg = spec.get("kind"), spec.get("arg")
    if kind == "pr_open":
        return PrOpen()
    if kind == "pr_open_and_shell_ok":
        return PrOpen() & ShellOk(arg)
    return ShellOk(arg or f"test -s {RESULT_FILE}")


def _gate_file(spec: dict) -> str:
    """The file a shell gate asserts on (``test -s <file>`` → ``<file>``)."""
    arg = str(spec.get("arg") or "")
    return arg.rsplit(" ", 1)[-1] if arg else RESULT_FILE


def gate_prose(spec: dict) -> str:
    """How the gate reads in the Goal cell's exit criteria.

    Phrased to be *derivation-stable*: feeding this prose back through
    :func:`gate_spec` must return the same spec, so saving a drafted Goal
    unedited never silently re-specs the gate. (In particular it avoids the
    word "test", which is one of the repo-shaped keywords.)
    """
    if spec.get("kind") == "pr_open":
        return "an open PR exists on the launch branch"
    if spec.get("kind") == "pr_open_and_shell_ok":
        return (f"an open PR exists on the launch branch and {_gate_file(spec)} "
                "is non-empty in the workspace")
    return (f"`{_gate_file(spec)}` is non-empty in the workspace — write the "
            "answer there")


def fallback_goal(text: str, spec: dict) -> str:
    """A deterministic Goal draft: used when no model is available (offline
    gates, pinned slugs, an unusable router response). Deliberately phrased so
    re-deriving the gate from this prose yields ``spec`` again."""
    return f"Deliverables: {text.strip()}\n\nDone when: {gate_prose(spec)}."


def _repo_root() -> Path:
    override = os.environ.get("THREADS_LAUNCH_REPO")
    if override:
        return Path(override).expanduser().resolve()
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True, timeout=5)
    if proc.returncode:
        raise RuntimeError(
            "launch needs THREADS_LAUNCH_REPO or a git cwd to spawn an executor")
    return Path(proc.stdout.strip())


def _spec_seed(rec: dict, slug: str, interpretation: str) -> str:
    branch = f"{slug}/{_short(rec['id'])}"
    spec = gate_spec_for(rec)
    goal = rec.get("goal") or fallback_goal(rec["text"], spec)
    return (
        f"# Launched thread: {slug}\n\n{rec['text']}\n\n"
        f"## Goal (deliverables + exit criteria)\n{goal}\n\n"
        f"Gate (externally checked, not your self-report): {spec['name']}\n\n"
        f"## Router interpretation\n{interpretation}\n\n"
        f"## Launcher stamp\n"
        f"THREADS_SLUG={slug} · branch `{branch}` · intent `{rec['id']}`.\n"
        "Export THREADS_SLUG in any tmux/session env you spawn. For "
        f"question-shaped work write the final answer to `{RESULT_FILE}`.\n")


def _full_auto(rec: dict, slug: str, interpretation: str) -> str:
    """Submit the intent to the concierge pool; record the tid on the thread."""
    from concierge.api import Pool
    branch = f"{slug}/{_short(rec['id'])}"
    # the gate comes off the record, so a pre-spawn Goal edit is what the
    # executor is actually gated on (board DoD 3).
    spec = gate_spec_for(rec)
    gate_name, gate = spec["name"], gate_object(spec)
    budget = float(os.environ.get("THREADS_LAUNCH_BUDGET_USD", "20"))
    # NB: THREADS_SLUG is stamped into the spec text and the branch name (the
    # deterministic weave keys off the concierge tid + branch, not a runtime
    # env var) — so no concierge-core env plumbing is needed.
    tid = Pool(home=config.concierge_home()).submit(
        _spec_seed(rec, slug, interpretation),
        title=f"thread launch: {slug}", repo=_repo_root(), branch=branch,
        gate=gate, budget_usd=budget)
    note.add_note(
        slug, f"Full-auto executor submitted: concierge `{tid}`.\n\nGate: {gate_name}",
        title="full-auto executor started", status="ongoing",
        session_id=tid, branch=branch)
    return tid


def _foyer_url() -> str:
    try:
        proc = subprocess.run(["foyer", "url"], capture_output=True, text=True,
                              timeout=5)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "foyer unavailable — attach with tmux"


def _copilot(rec: dict, slug: str, interpretation: str) -> str:
    """Spawn a tmux ``claude`` seeded with the intent in a fresh worktree."""
    repo = _repo_root()
    branch = f"{slug}/{_short(rec['id'])}"
    worktree = config.launch_worktrees_dir() / rec["id"]
    worktree.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "worktree", "add", str(worktree), "-b", branch],
                   cwd=repo, check=True, capture_output=True, text=True)
    session = f"thread-{slug[:24]}-{_short(rec['id'])[-6:]}"
    seed = (f"You are the copilot for thread `{slug}` (THREADS_SLUG={slug}).\n\n"
            f"Intent: {rec['text']}\n\n{interpretation}")
    command = f"cd {str(worktree)!r} && THREADS_SLUG={slug!r} claude {seed!r}"
    subprocess.run(["tmux", "new-session", "-d", "-s", session, command],
                   check=True)
    url = _foyer_url()
    # cached on the record so the board can render the deepest-live-link column
    # without shelling out to `foyer url` once per row on every page load.
    rec["foyer_url"] = url
    rec["worktree"] = str(worktree)
    note.add_note(
        slug, f"Copilot tmux session `{session}` in `{worktree}`.\n\nFoyer: {url}",
        title="copilot executor started", status="ongoing",
        session_id=session, cwd=str(worktree), branch=branch)
    return session


# --------------------------------------------------------------------------- #
# the async pipeline: route → note zero + interpretation → spawn → monitor
# --------------------------------------------------------------------------- #
def _fail(rec: dict, exc: BaseException) -> None:
    """A route/spawn failure lands on the thread + flares — never silent."""
    rec.update(state="failed", terminal_state="failed", error=str(exc),
               updated_at=_now())
    _write(rec)
    slug = (rec.get("resolved_slug") or rec.get("requested_slug")
            or f"launch-{_short(rec['id'])}")
    try:
        note.add_note(slug, f"Launcher failed: {type(exc).__name__}: {exc}",
                      title="launch failed", status="failed")
    except Exception:
        pass
    try:
        subprocess.run(["flare", f"thread launch {rec['id']} failed: {exc}",
                        "--sev", "warn"], timeout=10)
    except Exception:
        pass


def process_intent(intent_id: str, *, runner=summarize.default_runner) -> dict:
    """Route the intent, seed the thread, and spawn its executor."""
    rec = load_intent(intent_id)
    try:
        slug, route, interpretation, drafted_goal = _route(rec, runner=runner)
        branch = f"{slug}/{_short(rec['id'])}"
        # draft-and-veto: the router's Goal is immediately operative, but it
        # never overwrites an edit Daniel already made (the board can edit a
        # row while routing is still in flight).
        if rec.get("goal_state") != GOAL_EDITED:
            rec.update(goal=drafted_goal, goal_state=GOAL_DRAFTED)
        rec.update(resolved_slug=slug, route=route, state="routed",
                   updated_at=_now())
        _write(rec)
        # note zero — the intent text, carrying the session linkage.
        note.add_note(slug, rec["text"], title="intent (note zero)",
                      status="ongoing", session_id=rec["id"], branch=branch)
        # the router's interpretation (reading + assumptions + chosen gate).
        interp_body = (f"Reading + assumptions:\n\n{interpretation}\n\n"
                       f"Goal (deliverables + exit criteria):\n\n{rec['goal']}")
        if rec["mode"] == "full-auto":
            interp_body += f"\n\nChosen gate: {gate_spec_for(rec)['name']}"
        note.add_note(slug, interp_body, title="router interpretation",
                      status="ongoing")
        if rec.get("dry_run"):
            handle = f"dry-run:{rec['mode']}"
        elif rec["mode"] == "copilot":
            handle = _copilot(rec, slug, interpretation)
        else:
            handle = _full_auto(rec, slug, interpretation)
        rec.update(executor_handle=handle, state="spawned", updated_at=_now())
        _write(rec)
        if rec["mode"] == "full-auto" and not rec.get("dry_run"):
            _enqueue_monitor(rec["id"], handle)
    except Exception as exc:  # noqa: BLE001 — every failure must surface
        _fail(rec, exc)
    return rec


def _enqueue_monitor(intent_id: str, tid: str) -> None:
    # Same seam as enqueue_intent: offline gates run process_intent against a
    # throwaway spool, and a detached monitor would outlive it (its env
    # snapshot keeps pointing at the deleted temp dirs and it fails loudly).
    if os.environ.get("THREADS_DISABLE_ENQUEUE"):
        return
    subprocess.Popen(
        [sys.executable, "-m", "threads.launch", "--monitor", intent_id, tid],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True, env={**os.environ})


def monitor_full_auto(intent_id: str, tid: str) -> None:
    """Block on the concierge task and write its terminal note (gate settling
    writes the note, not the worker's self-report)."""
    from concierge.api import Pool
    rec = load_intent(intent_id)
    try:
        task = asyncio.run(Pool(home=config.concierge_home()).wait(tid))
        status = task.get("status")
        state = "result" if status == "done" else (
            "blocked" if status == "blocked" else "failed")
        detail = (task.get("result_text") or task.get("status_detail")
                  or status or "")
        note.add_note(
            rec.get("resolved_slug") or f"launch-{_short(intent_id)}",
            f"Concierge `{tid}` settled `{status}`.\n\n{detail}",
            title=f"launch {state}", status=state, session_id=tid)
        rec.update(state="terminal", terminal_state=state, updated_at=_now())
        _write(rec)
    except Exception as exc:  # noqa: BLE001
        _fail(rec, exc)


# --------------------------------------------------------------------------- #
# the Goal cell — inline edit is the veto/redirect surface
# --------------------------------------------------------------------------- #
def read_task(tid: str) -> dict | None:
    """One concierge task record, read straight off disk (offline, no import)."""
    path = config.concierge_home() / "tasks" / f"{tid}.json"
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _gate_settled(task: dict | None) -> bool:
    """True once the executor has passed its gate (then a re-derived gate would
    be revisionist — the row is already terminal on the old contract)."""
    if not task:
        return False
    result = task.get("gate_result") or {}
    return bool(result.get("passed")) or task.get("status") == "done"


def set_goal(intent_id: str, text: str, *, now: str | None = None) -> dict:
    """Edit one intent's Goal cell. This is the whole veto/redirect surface.

    * **Pre-spawn** (no executor handle yet): the edit re-specs the task — the
      gate is re-derived from the edited prose and stored on the record, so the
      executor is submitted against the *edited* goal (:func:`_full_auto` reads
      the record).
    * **Post-spawn**: the edit is delivered to the running worker as a
      ``pool.msg`` and the row is flagged so the discrepancy is visible. The
      gate is re-derived only while the executor has not passed it yet.

    Never raises on a delivery failure — an undeliverable edit still lands on
    the record, flags the row, and records why (silence is the failure mode
    this whole package exists to prevent).
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("goal text is empty")
    rec = load_intent(intent_id)
    stamp = now or _now()
    previous = rec.get("goal")
    spawned = bool(rec.get("executor_handle"))
    rec.setdefault("goal_history", []).append(
        {"at": stamp, "text": text, "previous": previous,
         "phase": "post-spawn" if spawned else "pre-spawn"})
    rec.update(goal=text, goal_state=GOAL_EDITED, goal_edited_at=stamp,
               updated_at=stamp)

    task = read_task(rec["executor_handle"]) if spawned else None
    settled = _gate_settled(task)
    if not settled:
        rec["gate"] = gate_spec(text, rec["text"])
        rec["gate_rederived_at"] = stamp

    body = text
    if spawned:
        # the discrepancy between what the executor was launched on and what
        # Daniel now wants is exactly what the flag makes visible.
        rec["goal_flagged"] = True
        rec.pop("goal_msg_error", None)
        body = (f"Goal edited on the board — this supersedes the goal you were "
                f"launched with:\n\n{text}\n\n"
                + ("Your gate is unchanged (already passed)." if settled else
                   f"Gate now checked as: {gate_spec_for(rec)['name']}"))
        if rec.get("mode") == "full-auto" and not rec.get("dry_run") and task:
            try:
                from concierge.api import Pool
                Pool(home=config.concierge_home()).msg(rec["executor_handle"], body)
                rec["goal_msg_delivered_at"] = stamp
            except Exception as exc:  # noqa: BLE001 — never lose the edit
                rec["goal_msg_error"] = f"{type(exc).__name__}: {exc}"
        else:
            rec["goal_msg_error"] = (
                "no concierge mailbox for this executor "
                f"({rec.get('mode')} handle {rec.get('executor_handle')}) — "
                "deliver the edit in the session itself")
    _write(rec)

    slug = rec.get("resolved_slug")
    if slug:
        try:
            note.add_note(
                slug, body,
                title=f"goal edited ({'post' if spawned else 'pre'}-spawn)",
                status="ongoing", session_id=rec["id"])
        except Exception:  # noqa: BLE001 — a note failure never loses the edit
            pass
    return rec


# --------------------------------------------------------------------------- #
# veto affordances — detach / merge-into-thread
# --------------------------------------------------------------------------- #
def detach(intent_id: str) -> dict:
    rec = load_intent(intent_id)
    rec.update(resolved_slug=None, state="detached", updated_at=_now())
    _write(rec)
    return rec


def merge_into(intent_id: str, slug: str) -> dict:
    rec = load_intent(intent_id)
    old = rec.get("resolved_slug")
    slug = slug.strip().lower()
    rec.update(resolved_slug=slug, state="merged", updated_at=_now())
    _write(rec)
    note.add_note(
        slug, f"Merged launched intent `{intent_id}` (was `{old}`).\n\n{rec['text']}",
        title="intent merged into thread", status="ongoing")
    return rec


# --------------------------------------------------------------------------- #
# termination sweep — a dormant launched intent with no terminal note
# --------------------------------------------------------------------------- #
def termination_sweep(*, now: datetime | None = None,
                      flare_warning: bool = True) -> list[str]:
    """Flag every launched intent past ``terminal_deadline_days`` with no
    terminal note: a ``BLOCKED-ON-DANIEL`` thread note (desk sweeps it) + one
    ``--sev warn`` flare. Idempotent — flags each intent at most once."""
    now = now or datetime.now(timezone.utc)
    deadline = config.load_config().terminal_deadline_days
    flagged = []
    for rec in load_intents():
        if rec.get("terminal_state") in TERMINAL or rec.get("sweep_flagged_at"):
            continue
        if rec.get("dry_run") or rec.get("state") in ("detached",):
            continue
        try:
            created = datetime.fromisoformat(
                rec["created_at"].replace("Z", "+00:00"))
        except (KeyError, ValueError, AttributeError):
            continue
        if (now - created).total_seconds() <= deadline * 86400:
            continue
        slug = (rec.get("resolved_slug") or rec.get("requested_slug")
                or f"launch-{_short(rec['id'])}")
        body = (
            f"BLOCKED-ON-DANIEL: launched intent `{rec['id']}` is dormant past "
            f"the {deadline}-day terminal deadline with no result/blocked/failed "
            f"note. Detach, merge, or intervene.\n\n{rec['text']}")
        try:
            note.add_note(slug, body,
                          title="launch termination contract violated",
                          status="blocked")
        except Exception:
            continue
        rec["sweep_flagged_at"] = _now()
        _write(rec)
        flagged.append(rec["id"])
        if flare_warning:
            try:
                subprocess.run(
                    ["flare", f"launched thread {slug} missed its terminal "
                     f"deadline ({deadline}d)", "--sev", "warn"], timeout=10)
            except Exception:
                pass
    return flagged


# --------------------------------------------------------------------------- #
# gate hook — offline, no model, no network
# --------------------------------------------------------------------------- #
def _intent_consistent(item: dict, *, now: datetime) -> bool:
    """An intent is consistent iff it has a resolved slug + executor handle, a
    failure note, was vetoed, or is still legitimately in-flight (async)."""
    if item.get("resolved_slug") and item.get("executor_handle"):
        return True
    if item.get("terminal_state") == "failed" and item.get("error"):
        return True
    if item.get("state") in ("detached", "merged"):
        return True
    # in-flight grace: routing/spawning is async and may not have landed yet.
    if item.get("state") in ("accepted", "routed"):
        try:
            upd = datetime.fromisoformat(
                item.get("updated_at", "").replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return False
        return (now - upd).total_seconds() < INFLIGHT_GRACE_SECONDS
    return False


def launch_check() -> tuple[bool, str]:
    """Offline gate (no model, no network, no executor): one synthetic
    --dry-run launch proves the accept path returns <100ms, then assert every
    intent in the spool is consistent (a resolved slug + executor handle, a
    failure note, a veto, or still legitimately in-flight).

    The synthetic intent is a pure latency probe — it is removed immediately and
    never routed, so the check writes nothing durable to the spool.
    """
    now = datetime.now(timezone.utc)
    start = time.perf_counter()
    rec = accept("synthetic launcher health check", slug="launcher-check",
                 dry_run=True, enqueue=False)
    latency_ms = (time.perf_counter() - start) * 1000
    _remove_intent(rec["id"])  # probe only — leave no trace in the spool

    intents = load_intents()
    problems = [item["id"] for item in intents
                if not _intent_consistent(item, now=now)]
    total = len(intents)
    ok = latency_ms < 100 and not problems
    lines = [
        f"launch --check {'OK' if ok else 'FAIL'}",
        f"accept latency: {latency_ms:.2f} ms (need <100 ms)",
        f"intent spool consistent: {total - len(problems)}/{total}",
    ]
    if problems:
        lines.append("inconsistent intents (no slug+handle / failure / in-flight):")
        lines.extend(f"  - {p}" for p in problems[:20])
    return ok, "\n".join(lines)


# --------------------------------------------------------------------------- #
# deterministic launcher-stamp index (consumed by threads.weave)
# --------------------------------------------------------------------------- #
def stamp_index() -> tuple[dict[str, str], set[str]]:
    """``(tid → slug, {launched slugs})`` for the deterministic weave pass.

    A full-auto executor's handle is its concierge tid (mapped from a
    ``workspaces/<tid>`` cwd); every launched slug also owns the
    ``<slug>/<short-ulid>`` branch namespace.
    """
    tid_to_slug: dict[str, str] = {}
    launched: set[str] = set()
    for rec in load_intents():
        slug = rec.get("resolved_slug")
        if not slug or rec.get("dry_run"):
            continue
        launched.add(slug)
        handle = rec.get("executor_handle")
        if (rec.get("mode") == "full-auto" and isinstance(handle, str)
                and not handle.startswith("dry-run:")):
            tid_to_slug[handle] = slug
    return tid_to_slug, launched


# --------------------------------------------------------------------------- #
# `python -m threads.launch` — the detached processor/monitor entrypoints
# --------------------------------------------------------------------------- #
def _main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--process":
        process_intent(sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1] == "--monitor":
        monitor_full_auto(sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    _main()
