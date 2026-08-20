"""gitland: the goal-capture PR vehicle (jarvis #50) — landing worktree,
batched commit+push, PR ensure, stacking on an open PR, fail-soft retry."""

from __future__ import annotations

import subprocess

import pytest

from mailroom import gitland, ingest, route, spool
from mailroom.actuators import append_goal_bullet

from mailroom_testkit import CH, NOW, FakeSlack, FakeTodoist, slack_msg


def _sh(cwd, *args):
    subprocess.run(args, cwd=str(cwd), check=True, capture_output=True, text=True)


def _out(cwd, *args) -> str:
    return subprocess.run(args, cwd=str(cwd), capture_output=True,
                          text=True).stdout


@pytest.fixture
def goal_repo(tmp_path):
    """Bare origin + a 'deployed checkout' clone shaped like the monorepo."""
    origin = tmp_path / "origin.git"
    _sh(tmp_path, "git", "init", "--bare", "-q", "-b", "main", str(origin))
    co = tmp_path / "checkout"
    _sh(tmp_path, "git", "init", "-q", "-b", "main", str(co))
    _sh(co, "git", "config", "user.email", "t@t")
    _sh(co, "git", "config", "user.name", "t")
    gdir = co / "jarvis-os" / "goals"
    gdir.mkdir(parents=True)
    (gdir / "phd-thesis.md").write_text("# goal\n\n## Parked follow-ups\n")
    _sh(co, "git", "add", "-A")
    _sh(co, "git", "commit", "-qm", "seed")
    _sh(co, "git", "remote", "add", "origin", str(origin))
    _sh(co, "git", "push", "-qu", "origin", "main")
    return co


def _origin_goal_file(co) -> str:
    _sh(co, "git", "fetch", "-q", "origin")
    return _out(co, "git", "show",
                f"origin/{gitland.BRANCH}:jarvis-os/goals/phd-thesis.md")


def _stub_pr(calls, url="https://github.com/x/pull/1", err=None):
    def ensurer(repo_dir, branch, title, body):
        calls.append({"branch": branch, "title": title, "body": body})
        return url, err

    return ensurer


def _land_one(co, text, calls):
    lander = gitland.GoalLander(repo_dir=co, goals_rel="jarvis-os/goals",
                                pr_ensurer=_stub_pr(calls))
    gd = lander.ensure_open()
    assert gd is not None, lander.error
    assert append_goal_bullet("phd-thesis", text, now=NOW, goals_dir=gd)
    lander.record("phd-thesis", text)
    return lander.close(now=NOW)


def test_lands_batch_as_branch_push_and_pr(goal_repo):
    calls = []
    pushed, pr, err = _land_one(goal_repo, "first capture", calls)
    assert pushed and err is None and pr == "https://github.com/x/pull/1"
    assert calls and calls[0]["branch"] == gitland.BRANCH
    assert "first capture" in calls[0]["body"]
    assert "first capture" in _origin_goal_file(goal_repo)
    # the landing worktree and local branch are cleaned up after the push
    assert not (goal_repo / ".claude" / "worktrees" / gitland.WORKTREE_NAME).exists()
    assert _out(goal_repo, "git", "branch", "--list", gitland.BRANCH).strip() == ""


def test_stacks_on_open_pr_branch(goal_repo):
    calls = []
    _land_one(goal_repo, "first capture", calls)
    # sweep hasn't merged run 1's PR yet → run 2 stacks on its branch
    _land_one(goal_repo, "second capture", calls)
    content = _origin_goal_file(goal_repo)
    assert "first capture" in content and "second capture" in content


def test_no_captures_is_a_noop(goal_repo):
    lander = gitland.GoalLander(repo_dir=goal_repo, goals_rel="jarvis-os/goals",
                                pr_ensurer=_stub_pr([]))
    assert lander.ensure_open() is not None
    pushed, pr, err = lander.close(now=NOW)
    assert not pushed and pr is None
    assert _out(goal_repo, "git", "ls-remote", "origin",
                f"refs/heads/{gitland.BRANCH}").strip() == ""


def test_pr_ensure_failure_still_counts_as_landed(goal_repo):
    calls = []
    lander = gitland.GoalLander(repo_dir=goal_repo, goals_rel="jarvis-os/goals",
                                pr_ensurer=_stub_pr(calls, url=None, err="gh down"))
    gd = lander.ensure_open()
    append_goal_bullet("phd-thesis", "capture", now=NOW, goals_dir=gd)
    lander.record("phd-thesis", "capture")
    pushed, pr, err = lander.close(now=NOW)
    assert pushed  # bullets are safe on the remote branch
    assert pr is None and "gh down" in err


def test_fail_soft_when_repo_missing(tmp_path):
    lander = gitland.GoalLander(repo_dir=tmp_path / "nope", goals_rel="x")
    assert lander.ensure_open() is None
    assert lander.error
    assert lander.ensure_open() is None  # cached failure, no per-capture retry
    pushed, pr, err = lander.close()
    assert not pushed


# --------------------------------------------------------------------------- #
# route() integration: defer → land → mark routed; failure → stays pending
# --------------------------------------------------------------------------- #
def _ingest_goal_capture(text):
    slack = FakeSlack([slack_msg("100", text=text)])
    ingest.ingest(backfill=True, client=slack, todoist_client=FakeTodoist(),
                  transcriber=lambda w: "x", now=NOW)
    return slack


def test_route_defers_to_lander_and_marks_routed_after_push(
        env, triage_runner, note_calls, goal_repo):
    env.add_goal("phd-thesis")  # slug validation reads the deployed goals dir
    calls = []
    lander = gitland.GoalLander(repo_dir=goal_repo, goals_rel="jarvis-os/goals",
                                pr_ensurer=_stub_pr(calls))
    slack = _ingest_goal_capture("goal: prioritize the thesis chapter")
    res = route.route(runner=triage_runner, todoist_client=FakeTodoist(),
                      slack_client=slack, note_runner=note_calls,
                      goal_lander=lander, now=NOW)
    rec = spool.load_thought(f"slack-{CH}-100")
    assert rec["route"]["action"] == "goal-bullet"
    assert rec["route"]["pr"] == "https://github.com/x/pull/1"
    assert res.goal_pr == "https://github.com/x/pull/1" and res.routed == 1
    assert "prioritize the thesis chapter" in _origin_goal_file(goal_repo)
    # the deployed checkout's goal file is NEVER written in-place anymore
    assert "via mailroom" not in (env.goals / "phd-thesis.md").read_text()


def test_route_leaves_capture_pending_when_lander_fails(
        env, triage_runner, note_calls, tmp_path):
    env.add_goal("phd-thesis")
    broken = gitland.GoalLander(repo_dir=tmp_path / "norepo", goals_rel="g")
    slack = _ingest_goal_capture("goal: retry me next run")
    res = route.route(runner=triage_runner, todoist_client=FakeTodoist(),
                      slack_client=slack, note_runner=note_calls,
                      goal_lander=broken, now=NOW)
    rec = spool.load_thought(f"slack-{CH}-100")
    assert not rec.get("route")  # unrouted → the next 2-hourly run retries
    assert res.routed == 0
    assert any("goal lander" in e for e in res.errors)
    assert "via mailroom" not in (env.goals / "phd-thesis.md").read_text()
