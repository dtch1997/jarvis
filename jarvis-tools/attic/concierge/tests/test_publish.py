"""The harness publish-pass and the codex-permissions enforcement (issue #8):
separate doing from publishing.

Publish-pass runs against a REAL local git repo (a bare repo as origin) with a
fake `gh` on PATH for the PR-open/-view step — no live GitHub. Also covers the
submit/delegate rejection, the reconciler reroute backstop, the env scrub, and
the codex cost stamp drawing the daily cap.
"""
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from concierge import Pool, delegation, publish, reconcile, runtime
from concierge.gates import PrMerged, PrOpen, ShellOk
from concierge.records import Home, new_task, now_iso
from concierge.runtime import WorkerState

FIXTURES = Path(__file__).parent / "fixtures"
GH_STUB = FIXTURES / "gh_stub.py"


# -- git/gh scaffolding: a bare origin + a workspace clone + a stub gh on PATH --

def _git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True,
                   capture_output=True, text=True)


def _setup_repo(tmp_path, home, tid, *, with_commit=True):
    """Bare origin seeded with a `main`, then a workspace clone on branch
    pool/<tid> (optionally with a commit beyond main). Returns (origin, ws)."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(origin)], check=True)

    seed = tmp_path / "seed"
    subprocess.run(["git", "init", "-q", "-b", "main", str(seed)], check=True)
    _git(seed, "config", "user.email", "t@t.t")
    _git(seed, "config", "user.name", "t")
    (seed / "README.md").write_text("base\n")
    _git(seed, "add", "-A")
    _git(seed, "commit", "-q", "-m", "base")
    _git(seed, "remote", "add", "origin", str(origin))
    _git(seed, "push", "-q", "origin", "main")

    ws = home.workspace(tid)
    subprocess.run(["git", "clone", "-q", str(origin), str(ws)], check=True)
    _git(ws, "config", "user.email", "w@w.w")
    _git(ws, "config", "user.name", "w")
    _git(ws, "checkout", "-q", "-b", f"pool/{tid}", "main")
    if with_commit:
        (ws / "work.txt").write_text("the worker did the work\n")
        _git(ws, "add", "-A")
        _git(ws, "commit", "-q", "-m", "work")
    return origin, ws


def _stub_gh_on_path(tmp_path, monkeypatch):
    """Put the fake gh first on PATH (a shim named `gh` → gh_stub.py). Both the
    harness publish and PrOpen.check pick it up from the subprocess PATH."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    shim = bindir / "gh"
    shim.write_text(f'#!/usr/bin/env bash\nexec {sys.executable} {GH_STUB} "$@"\n')
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC)
    state = tmp_path / "gh_state.json"
    calls = tmp_path / "gh_calls.txt"
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("GH_STUB_STATE", str(state))
    monkeypatch.setenv("GH_STUB_CALLS", str(calls))
    return state, calls


def _codex_task(home, tid, origin, gate):
    task = new_task(tid, "codex publish task", gate.to_json(),
                    {"usd": 10, "wall_minutes": 60},
                    {"repo": str(origin), "base": "main", "branch": f"pool/{tid}",
                     "access": "readwrite"}, backend="codex")
    task["status"] = "running"
    task["attempts"].append({"n": 1, "pid": 1, "started": now_iso(),
                             "session_id": "th-1", "cost_usd": 0.01,
                             "result": None, "log": f"logs/{tid}/attempt-1"})
    home.save(task)
    return task


class _FakeWorker:
    """A worker that has already exited cleanly with a result."""
    def __init__(self, text="did the work", output=None):
        self.started = now_iso()
        self._text, self._output = text, output

    def poll(self):
        return WorkerState(alive=False, ended=True, session_id="th-1", cost_usd=0.01,
                           error=None, started=self.started, text=self._text,
                           output=self._output)

    def sync(self, task, state):
        pass

    def kill(self):
        pass


def _no_real_spawn(monkeypatch):
    """Stop _refresh_running's fail-path resume from spawning a real worker."""
    def fake_spawn(cls, home, task, text, cfg, resume=None, output_schema=None):
        task["attempts"].append({"n": len(task["attempts"]) + 1, "pid": 2,
                                 "started": now_iso(), "session_id": None,
                                 "cost_usd": None, "result": None, "log": "x"})
        return _FakeWorker()
    monkeypatch.setattr(runtime.Worker, "spawn", classmethod(fake_spawn))


# -- publish-pass happy path --

def test_publish_pass_opens_pr_and_gate_passes(tmp_path, monkeypatch):
    home = Home(tmp_path / "home")
    origin, ws = _setup_repo(tmp_path, home, "t-pub")
    state, calls = _stub_gh_on_path(tmp_path, monkeypatch)
    task = _codex_task(home, "t-pub", origin, ShellOk("test -f work.txt") & PrOpen())
    monkeypatch.setattr(runtime.Worker, "attach",
                        classmethod(lambda cls, home, task: _FakeWorker(output={"k": "v"})))

    reconcile._refresh_running(home, {}, task)

    saved = home.load("t-pub")
    assert saved["status"] == "done"                      # PrOpen now passes
    assert saved["published"]["branch"] == "pool/t-pub"
    assert saved["published"]["pr_url"].startswith("https://example.test/")
    assert saved["published"]["at"]
    assert saved["links"]["pr"] == saved["published"]["pr_url"]
    # the branch was actually pushed to origin
    r = subprocess.run(["git", "-C", str(origin), "branch", "--list", "pool/t-pub"],
                       capture_output=True, text=True)
    assert "pool/t-pub" in r.stdout
    # exactly one PR created; body carries the worker's structured output
    assert calls.read_text().count("create ") == 1


def test_publish_bare_pr_open_gate(tmp_path, monkeypatch):
    """A gate that is JUST PrOpen: without_publishable() → Always, so the only
    guard is the has-commit check."""
    home = Home(tmp_path / "home")
    origin, ws = _setup_repo(tmp_path, home, "t-bare")
    _stub_gh_on_path(tmp_path, monkeypatch)
    task = _codex_task(home, "t-bare", origin, PrOpen())
    monkeypatch.setattr(runtime.Worker, "attach",
                        classmethod(lambda cls, home, task: _FakeWorker()))

    reconcile._refresh_running(home, {}, task)
    assert home.load("t-bare")["status"] == "done"


# -- no commit beyond base → no publish (a normal gate failure) --

def test_no_commit_no_publish(tmp_path, monkeypatch):
    home = Home(tmp_path / "home")
    origin, ws = _setup_repo(tmp_path, home, "t-empty", with_commit=False)
    state, calls = _stub_gh_on_path(tmp_path, monkeypatch)
    task = _codex_task(home, "t-empty", origin, PrOpen())
    monkeypatch.setattr(runtime.Worker, "attach",
                        classmethod(lambda cls, home, task: _FakeWorker(text="nothing")))
    _no_real_spawn(monkeypatch)

    reconcile._refresh_running(home, {}, task)

    saved = home.load("t-empty")
    assert saved["status"] != "done"                      # PrOpen never opened
    assert saved.get("published") is None
    assert not calls.exists() or calls.read_text() == ""  # no gh pr create
    # origin got no pool branch
    r = subprocess.run(["git", "-C", str(origin), "branch", "--list", "pool/t-empty"],
                       capture_output=True, text=True)
    assert r.stdout.strip() == ""


# -- local gate component fails → no publish --

def test_local_gate_fail_blocks_publish(tmp_path, monkeypatch):
    home = Home(tmp_path / "home")
    origin, ws = _setup_repo(tmp_path, home, "t-localfail")
    state, calls = _stub_gh_on_path(tmp_path, monkeypatch)
    # the local ShellOk fails (missing file) even though a commit exists
    task = _codex_task(home, "t-localfail", origin,
                       ShellOk("test -f MISSING") & PrOpen())
    monkeypatch.setattr(runtime.Worker, "attach",
                        classmethod(lambda cls, home, task: _FakeWorker()))
    _no_real_spawn(monkeypatch)

    reconcile._refresh_running(home, {}, task)

    saved = home.load("t-localfail")
    assert saved["status"] != "done"
    assert saved.get("published") is None
    assert not calls.exists() or calls.read_text() == ""


# -- idempotent republish --

def test_idempotent_republish(tmp_path, monkeypatch):
    home = Home(tmp_path / "home")
    origin, ws = _setup_repo(tmp_path, home, "t-idem")
    state, calls = _stub_gh_on_path(tmp_path, monkeypatch)
    task = _codex_task(home, "t-idem", origin, PrOpen())

    first = publish.publish_branch(home, {}, task, notes="a")
    second = publish.publish_branch(home, {}, task, notes="a")

    assert first["pr_url"] == second["pr_url"]
    assert calls.read_text().count("create ") == 1         # never a duplicate PR


def test_has_commits(tmp_path):
    home = Home(tmp_path / "home")
    _, ws = _setup_repo(tmp_path, home, "t-hc", with_commit=True)
    assert publish.has_commits(ws, "main") is True
    _, ws2 = _setup_repo(tmp_path / "b", Home(tmp_path / "b" / "home"), "t-hc2",
                         with_commit=False)
    assert publish.has_commits(ws2, "main") is False


def test_publish_refuses_main_branch(tmp_path):
    home = Home(tmp_path / "home")
    origin, ws = _setup_repo(tmp_path, home, "t-main")
    task = home.load("t-main") if home.task_path("t-main").exists() else \
        _codex_task(home, "t-main", origin, PrOpen())
    task["workspace"]["branch"] = "main"
    with pytest.raises(publish.PublishError, match="refusing to publish"):
        publish.publish_branch(home, {}, task)


# -- reconciler reroute backstop --

def test_reroute_unpublishable_gate_to_claude(tmp_path):
    task = new_task("t-rr", "t", (ShellOk("x") & PrMerged()).to_json(),
                    {"usd": 1, "wall_minutes": 1},
                    {"repo": None, "base": "main", "branch": "b", "access": "readwrite"},
                    backend="codex")
    reconcile._enforce_backend_policy(task)
    assert task["backend"] == "claude"
    assert "rerouted" in task["status_detail"] and "pr_merged" in task["status_detail"]


def test_no_reroute_for_publishable_gate(tmp_path):
    # codex + PrOpen is legitimate — the harness publishes; do NOT reroute
    task = new_task("t-ok", "t", (ShellOk("x") & PrOpen()).to_json(),
                    {"usd": 1, "wall_minutes": 1},
                    {"repo": None, "base": "main", "branch": "b", "access": "readwrite"},
                    backend="codex")
    reconcile._enforce_backend_policy(task)
    assert task["backend"] == "codex"


def test_no_reroute_for_claude(tmp_path):
    task = new_task("t-cl", "t", PrMerged().to_json(),
                    {"usd": 1, "wall_minutes": 1},
                    {"repo": None, "base": "main", "branch": "b", "access": "readwrite"},
                    backend="claude")
    reconcile._enforce_backend_policy(task)
    assert task["backend"] == "claude"      # unchanged (it can push)


# -- submit-time rejection --

def test_submit_rejects_codex_unpublishable_gate(tmp_path):
    home = Home(tmp_path / "home")
    pool = Pool(home.root)
    with pytest.raises(ValueError, match="claude"):
        pool.submit("do it", backend="codex", gate=PrMerged())
    # PrOpen is accepted (harness publishes for codex)
    tid = pool.submit("do it", backend="codex", gate=PrOpen())
    assert pool.get(tid)["backend"] == "codex"
    # a local gate is accepted
    assert pool.get(pool.submit("do it", backend="codex", gate=ShellOk("true")))


def test_submit_default_backend_codex_rejects(tmp_path):
    home = Home(tmp_path / "home")
    (home.root / "config.yaml").write_text("default_backend: codex\n")
    pool = Pool(home.root)
    with pytest.raises(ValueError, match="publish"):
        pool.submit("do it", gate=PrMerged())          # inherits codex default


# -- delegate-time rejection --

def test_delegate_rejects_codex_unpublishable_gate(tmp_path):
    home = Home(tmp_path / "home")
    parent = new_task("t-parent", "p", {"kind": "always"},
                      {"usd": 20, "wall_minutes": 60},
                      {"repo": "git@x:r.git", "base": "main",
                       "branch": "pool/t-parent", "access": "readwrite"},
                      backend="claude")
    home.save(parent)
    with pytest.raises(delegation.DelegationError, match="claude"):
        delegation.delegate_child(home, parent, {}, title="leaf", spec="s",
                                   backend="codex", gate={"kind": "pr_merged"})
    # PrOpen child on codex is fine
    child = delegation.delegate_child(home, parent, {}, title="leaf", spec="s",
                                      backend="codex", gate={"kind": "pr_open"})
    assert child["backend"] == "codex"


def test_delegate_codex_parent_inherits_and_rejects(tmp_path):
    home = Home(tmp_path / "home")
    parent = new_task("t-parent", "p", {"kind": "always"},
                      {"usd": 20, "wall_minutes": 60},
                      {"repo": "git@x:r.git", "base": "main",
                       "branch": "pool/t-parent", "access": "readwrite"},
                      backend="codex")
    home.save(parent)
    # child inherits codex backend → a PrMerged gate must be refused
    with pytest.raises(delegation.DelegationError):
        delegation.delegate_child(home, parent, {}, title="leaf", spec="s",
                                   gate={"kind": "pr_merged"})


# -- env scrub --

def test_backend_config_scrubs_codex_env_file(tmp_path):
    cfg = {"env_file": str(tmp_path / ".env"), "concurrency": 4}
    # codex: env_file forced off by default (no secrets to a sandboxed leaf)
    assert runtime._backend_config(cfg, "codex")["env_file"] is None
    # claude: unchanged
    assert runtime._backend_config(cfg, "claude")["env_file"] == cfg["env_file"]
    # absent backend (legacy/None) unchanged too
    assert runtime._backend_config(cfg, None)["env_file"] == cfg["env_file"]
    # explicit per-backend override re-enables it
    cfg2 = {"env_file": None, "backends": {"codex": {"env_file": str(tmp_path / "k.env")}}}
    assert runtime._backend_config(cfg2, "codex")["env_file"] == str(tmp_path / "k.env")


def test_codex_worker_gets_no_env_file_secrets(tmp_path, monkeypatch):
    home = Home(tmp_path / "home")
    dotenv = tmp_path / ".env"
    dotenv.write_text("SECRET_KEY=supersecret\n")
    codex_task = new_task("t-c", "t", {"kind": "always"}, {"usd": 1, "wall_minutes": 1},
                          {"repo": None, "base": "main", "branch": "b", "access": "readwrite"},
                          backend="codex")
    claude_task = new_task("t-cl", "t", {"kind": "always"}, {"usd": 1, "wall_minutes": 1},
                           {"repo": None, "base": "main", "branch": "b", "access": "readwrite"})

    captured = {}

    class FakeProc:
        pid = 1

    def fake_popen(cmd, **kw):
        captured[kw["env"].get("CONCIERGE_TASK_ID")] = kw["env"]
        return FakeProc()

    monkeypatch.setattr(runtime.subprocess, "Popen", fake_popen)
    cfg = {"env_file": str(dotenv)}
    runtime.Worker.spawn(home, codex_task, "p", cfg)
    runtime.Worker.spawn(home, claude_task, "p", cfg)

    assert "SECRET_KEY" not in captured["t-c"]              # scrubbed for codex
    assert captured["t-cl"]["SECRET_KEY"] == "supersecret"  # preseeded for claude


# -- cost stamp draws the daily cap --

def test_codex_cost_default_draws_cap(tmp_path):
    # a codex attempt priced by the default rate stamps a nonzero cost, so
    # _spent_today (which gates dispatch against daily_usd_cap) sees real spend
    from concierge.backends import codex

    cfg = {}
    cfg.setdefault("codex_cost_per_mtoken", codex.CODEX_COST_PER_MTOKEN_DEFAULT)
    cost = codex._usage_cost({"input_tokens": 1_000_000, "output_tokens": 1_000_000}, cfg)
    assert cost == pytest.approx(1.25 + 10.0)              # documented GPT-5 rate
    assert cost > 0

    # the stamped cost flows into the daily-cap tally like any other attempt
    task = new_task("t-cost", "t", {"kind": "always"}, {"usd": 100, "wall_minutes": 60},
                    {"repo": None, "base": "main", "branch": "b", "access": "readwrite"},
                    backend="codex")
    task["attempts"].append({"n": 1, "pid": 1, "started": now_iso(),
                             "session_id": "th", "cost_usd": cost,
                             "result": "ok", "log": "x"})
    assert reconcile._spent_today([task]) == pytest.approx(11.25)
