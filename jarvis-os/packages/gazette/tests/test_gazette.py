import subprocess
from datetime import datetime, timedelta, timezone

import pytest

from gazette.config import Config
from gazette.lanes import (
    LABEL_APPROVAL,
    LABEL_AUTO,
    LABEL_BLOCKED,
    LABEL_DELAY,
    LABEL_VETO,
    PR,
    Lane,
    decide,
    path_matches,
    resolve_lane,
)
from gazette.notes import build_notes, compile_edition, digest, flare_body

NOW = datetime(2026, 8, 18, 8, 0, tzinfo=timezone.utc)


def make_pr(**kw) -> PR:
    defaults = dict(
        repo="ArcadiaImpact/jarvis",
        number=1,
        title="t",
        url="https://example.com/1",
        author="agent",
        created_at=NOW - timedelta(hours=48),
        labels=[],
        files=["docs/x.md"],
        checks="passing",
    )
    defaults.update(kw)
    return PR(**defaults)


# --------------------------------------------------------------------------- #
# path matching
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "path,glob,expected",
    [
        ("ops/cron.tab", "ops/**", True),
        ("ops", "ops/**", True),
        ("drops/cron.tab", "ops/**", False),
        ("CLAUDE.md", "CLAUDE.md", True),
        ("sub/dir/CLAUDE.md", "CLAUDE.md", True),  # bare names match at depth
        ("docs/a.md", "CLAUDE.md", False),
        ("conf/.env.prod", "**/.env*", True),
        (".env", "**/.env*", True),
        ("src/secrets.py", "**/*secret*", True),
    ],
)
def test_path_matches(path, glob, expected):
    assert path_matches(path, glob) is expected


# --------------------------------------------------------------------------- #
# lane resolution — two lanes since the 2026-08-19 rework
# --------------------------------------------------------------------------- #
def test_unlabeled_and_auto_label_are_auto_with_no_anomaly():
    cfg = Config()
    for labels in ([], [LABEL_AUTO]):
        lane, reasons = resolve_lane(labels, ["docs/a.md"], cfg)
        assert lane is Lane.AUTO and reasons == []


def test_requires_approval_label_and_legacy_blocked_alias():
    cfg = Config()
    for labels in ([LABEL_APPROVAL], [LABEL_BLOCKED]):
        lane, reasons = resolve_lane(labels, ["docs/a.md"], cfg)
        assert lane is Lane.APPROVAL and reasons == []


def test_retired_delay_label_is_auto_with_anomaly():
    lane, reasons = resolve_lane([LABEL_DELAY], ["docs/a.md"], Config())
    assert lane is Lane.AUTO
    assert any("retired lane:delay" in r for r in reasons)


def test_credential_paths_demote_to_approval_regardless_of_label():
    for labels in ([LABEL_AUTO], [LABEL_DELAY], []):
        lane, reasons = resolve_lane(labels, ["conf/.env.prod"], Config())
        assert lane is Lane.APPROVAL
        assert any("demoted to requires-approval" in r for r in reasons)
    # already labeled: demotion is not an anomaly
    lane, reasons = resolve_lane([LABEL_APPROVAL], ["conf/.env.prod"], Config())
    assert lane is Lane.APPROVAL and reasons == []


def test_behavior_shaping_paths_merge_with_annotation_not_delay():
    d = decide(make_pr(files=["CLAUDE.md"]), Config(), NOW)
    assert d.action == "merge"
    assert "behavior-shaping" in d.reason and "CLAUDE.md" in d.reason
    assert d.anomalies == []  # annotated, not anomalous


# --------------------------------------------------------------------------- #
# merge decisions
# --------------------------------------------------------------------------- #
def test_green_merges_immediately_regardless_of_age():
    cfg = Config()
    assert decide(make_pr(created_at=NOW - timedelta(minutes=5)), cfg, NOW).action == "merge"
    assert decide(make_pr(created_at=NOW - timedelta(days=30)), cfg, NOW).action == "merge"


def test_draft_and_veto_and_changes_requested_skip():
    cfg = Config()
    assert decide(make_pr(is_draft=True), cfg, NOW).action == "skip"
    assert decide(make_pr(labels=[LABEL_VETO]), cfg, NOW).action == "skip"
    assert decide(make_pr(review_decision="CHANGES_REQUESTED"), cfg, NOW).action == "skip"


def test_failing_or_pending_checks_wait():
    cfg = Config()
    d = decide(make_pr(checks="failing"), cfg, NOW)
    assert d.action == "wait" and "checks failing" in d.anomalies
    assert decide(make_pr(checks="pending"), cfg, NOW).action == "wait"


def test_requires_approval_never_merges():
    pr = make_pr(labels=[LABEL_APPROVAL], created_at=NOW - timedelta(days=30))
    d = decide(pr, Config(), NOW)
    assert d.action == "skip" and "requires approval" in d.reason
    legacy = make_pr(labels=[LABEL_BLOCKED], created_at=NOW - timedelta(days=30))
    assert decide(legacy, Config(), NOW).action == "skip"


def test_retired_delay_pr_merges_on_green():
    pr = make_pr(labels=[LABEL_DELAY], created_at=NOW - timedelta(hours=1))
    d = decide(pr, Config(), NOW)
    assert d.action == "merge"
    assert any("retired lane:delay" in a for a in d.anomalies)


# --------------------------------------------------------------------------- #
# notes rendering
# --------------------------------------------------------------------------- #
MERGED_ROW = {
    "repo": "ArcadiaImpact/jarvis", "number": 140, "title": "draft doc",
    "url": "u", "merged_at": NOW - timedelta(hours=3), "author": "agent",
    "labels": [],
}


def _edition():
    cfg = Config()
    open_prs = [
        make_pr(number=141, title="auto doc tweak",
                created_at=NOW - timedelta(hours=5), checks="pending"),
        make_pr(number=37, title="needs creds", labels=[LABEL_APPROVAL]),
    ]
    return cfg, open_prs, compile_edition(cfg, NOW, open_prs, [MERGED_ROW])


def test_notes_needs_you_is_approval_only_and_auto_is_ambient():
    cfg, open_prs, ed = _edition()
    text = build_notes(cfg, ed)
    assert text.index("## Needs you (1)") < text.index("## News")
    assert "jarvis#37" in text and "sits until you act" in text and "gh pr merge 37" in text
    # the auto PR is ambient pipeline, with the veto escape hatch
    assert "jarvis#141" in text and "next hourly sweep" in text and "--add-label veto" in text
    assert sorted(ed.visible_refs) == ["jarvis#141", "jarvis#37"]
    d = digest(cfg, NOW, open_prs, [MERGED_ROW])
    assert "merged 1" in d and "1 in pipeline" in d and "1 waiting on you" in d


def test_notes_version_line_rendered():
    cfg = Config()
    ed = compile_edition(cfg, NOW, [], [])
    line = "running v2026.08.18 (latest cut: v2026.08.18)"
    text = build_notes(cfg, ed, version_line=line)
    assert line in text
    assert line in flare_body(ed, version_line=line)


def test_notes_drafts_and_desk_and_news():
    cfg = Config()
    ed = compile_edition(cfg, NOW, [make_pr(is_draft=True)], [MERGED_ROW])
    assert ed.visible_refs == []  # drafts stay out of the edition entirely
    text = build_notes(cfg, ed, news="- you can now frobnicate (jarvis#140)",
                       desk_text="desk: 3 waiting")
    assert "you can now frobnicate" in text and "### All merges" in text
    assert "desk: 3 waiting" in text


def test_notes_quiet_state_and_flare_body():
    cfg = Config()
    ed = compile_edition(cfg, NOW, [], [])
    text = build_notes(cfg, ed)
    assert "nothing waits on you" in text and "nothing merged" in text
    assert "quiet" in flare_body(ed)  # empty morning is a one-liner

    _, _, busy = _edition()
    body = flare_body(busy, spool_path="/spool/x.md")
    assert body.splitlines()[0].startswith("☀️")
    assert "NEEDS YOU (1)" in body and "requires approval" in body
    assert "Full edition → /spool/x.md" in body


def test_editions_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("GAZETTE_HOME", str(tmp_path))
    from gazette import editions

    editions.record_edition(NOW, ["jarvis#141", "arsenal#37"])
    editions.record_edition(NOW, ["jarvis#141"])  # same date — no double count
    editions.record_edition(NOW + timedelta(days=1), ["jarvis#141"])
    assert editions.load_appearances() == {"jarvis#141": 2, "arsenal#37": 1}


def test_synthesize_degrades():
    from gazette import synthesize

    merged = [dict(MERGED_ROW, number=n) for n in range(3)]
    assert "jarvis#1: draft doc" in synthesize.news_prompt(merged)
    assert synthesize.synthesize(Config(synthesis_cmd=""), merged) is None
    assert synthesize.synthesize(Config(synthesis_cmd="no-such-binary-xyz"), merged) is None
    assert synthesize.synthesize(Config(), merged[:2]) is None  # too few merges


# --------------------------------------------------------------------------- #
# collector failure is loud, never falsely quiet (issue #21)
# --------------------------------------------------------------------------- #
COLLECTOR_ERR = "ArcadiaImpact/jarvis: gh CLI not found (searched PATH: /usr/bin:/bin)"


def test_gh_reports_collector_failure_with_searched_path(monkeypatch):
    """A missing gh yields (empty, warning, failed=True) — never an exception —
    and the warning names the PATH it searched, per issue #21 (a)."""
    from gazette import gh

    monkeypatch.setattr(gh, "_gh_bin", lambda: None)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    prs, warnings, failed = gh.list_open_prs("ArcadiaImpact/jarvis")
    assert prs == [] and failed is True
    assert "gh CLI not found" in warnings[0] and "/usr/bin:/bin" in warnings[0]
    merged, mwarn, mfailed = gh.list_merged_since("ArcadiaImpact/jarvis", NOW)
    assert merged == [] and mfailed is True


def test_collector_error_is_anomaly_and_edition_is_incomplete():
    """(b1)(b2): a collector failure surfaces in Anomalies, and the edition
    refuses to render 'Needs you (0)' / the quiet claim."""
    cfg = Config()
    ed = compile_edition(cfg, NOW, [], [], collector_errors=[COLLECTOR_ERR])
    assert ed.incomplete and ed.failed_repos == ["jarvis"]
    # promoted to an anomaly, not a footer-only warning
    assert any("collector failed" in a and "gh CLI not found" in a for a in ed.anomalies)
    assert ed.warnings == []

    text = build_notes(cfg, ed)
    assert "INCOMPLETE: collector failed for jarvis" in text
    assert "## Needs you (0)" not in text  # no falsely-reassuring quiet header
    assert "nothing waits on you today" not in text
    assert "## Anomalies" in text and "gh CLI not found" in text


def test_collector_error_flare_is_loud_not_quiet():
    """(b2): the flare for an incomplete edition is warn-shaped, never the
    'quiet: nothing needs you' one-liner."""
    cfg = Config()
    ed = compile_edition(cfg, NOW, [], [], collector_errors=[COLLECTOR_ERR])
    body = flare_body(ed, spool_path="/spool/x.md")
    assert "quiet" not in body
    assert "INCOMPLETE: collector failed for jarvis" in body
    assert "ANOMALIES (1)" in body
    assert "Full edition → /spool/x.md" in body


def test_incomplete_edition_still_shows_reachable_repo_needs_you():
    """A partial failure (one repo down) still surfaces the reachable repo's
    needs-you items — incomplete, but not blank."""
    cfg = Config()
    approval_pr = make_pr(repo="dtch1997/arsenal", number=37, title="ok repo",
                          labels=[LABEL_APPROVAL], created_at=NOW - timedelta(hours=5))
    ed = compile_edition(cfg, NOW, [approval_pr], [],
                         collector_errors=[COLLECTOR_ERR])
    assert ed.incomplete and ed.visible_refs == ["arsenal#37"]
    text = build_notes(cfg, ed)
    assert "INCOMPLETE" in text and "arsenal#37" in text
    assert "arsenal#37" in flare_body(ed)  # reachable needs-you still flared


# --------------------------------------------------------------------------- #
# delivery-log integrity: a failed collector earns no edition record (b3)
# --------------------------------------------------------------------------- #
class _FakeFlare:
    def __init__(self):
        self.calls = []

    def send(self, body, sev="info", source=""):
        self.calls.append({"body": body, "sev": sev, "source": source})


def _run_notes(monkeypatch, tmp_path, open_by_repo, merged_by_repo):
    """Drive cmd_notes with gh stubbed per-repo; returns (stdout, fake_flare)."""
    import sys
    from argparse import Namespace

    from gazette import cli, gh

    monkeypatch.setenv("GAZETTE_HOME", str(tmp_path))
    monkeypatch.setattr(cli, "_desk_digest", lambda: None)  # desk not part of this test
    monkeypatch.setattr(cli.versions, "status",
                        lambda cfg: "version status unavailable (test)")

    def fake_open(repo):
        return open_by_repo[repo]  # (prs, warnings, failed)

    def fake_merged(repo, since):
        return merged_by_repo[repo]

    monkeypatch.setattr(gh, "list_open_prs", fake_open)
    monkeypatch.setattr(gh, "list_merged_since", fake_merged)
    monkeypatch.setattr(gh, "unswept_lane_prs", lambda cfg: ([], []))

    fake_flare = _FakeFlare()
    monkeypatch.setitem(sys.modules, "flare", fake_flare)

    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli.cmd_notes(Namespace(flare=True))
    assert rc == 0
    return buf.getvalue(), fake_flare


def test_total_collector_failure_logs_no_edition_and_flares_warn(tmp_path, monkeypatch):
    """(b3): when every repo's PR collector fails, no edition is recorded —
    empty refs from failure are not a delivered edition — and the flare goes
    out --sev warn."""
    from gazette import editions

    repos = Config().github_repos  # the configured sweep set
    fail = ([], ["r: gh CLI not found (searched PATH: /usr/bin:/bin)"], True)
    open_by_repo = {r: fail for r in repos}
    merged_by_repo = {r: ([], [], False) for r in repos}

    stdout, flare = _run_notes(monkeypatch, tmp_path, open_by_repo, merged_by_repo)

    assert "INCOMPLETE" in stdout and "## Needs you (0)" not in stdout
    assert not editions.editions_path().exists()  # zero editions logged
    assert flare.calls and flare.calls[0]["sev"] == "warn"


def test_partial_failure_credits_only_reachable_repo(tmp_path, monkeypatch):
    """(b3): a reachable repo's PRs still land in the delivery log; the failed
    repo's PRs (none collected) do not appear in editions.jsonl."""
    from gazette import editions

    repos = Config().github_repos
    ok_pr = make_pr(repo=repos[1], number=37, title="reachable",
                    labels=[LABEL_APPROVAL], created_at=NOW - timedelta(hours=5))
    open_by_repo = {
        repos[0]: ([], ["j: gh CLI not found (searched PATH: /bin)"], True),
        repos[1]: ([ok_pr], [], False),
    }
    merged_by_repo = {r: ([], [], False) for r in repos}

    stdout, flare = _run_notes(monkeypatch, tmp_path, open_by_repo, merged_by_repo)

    assert "INCOMPLETE" in stdout
    assert flare.calls[0]["sev"] == "warn"
    appearances = editions.load_appearances()
    reachable_ref = f"{repos[1].split('/')[-1]}#37"
    assert appearances == {reachable_ref: 1}  # only the reachable repo credited


# --------------------------------------------------------------------------- #
# coverage: a lane-labelled PR in an unswept repo is loud, not invisible
# (2026-08-18: the monorepo cutover repointed github_repos and stranded
# ArcadiaImpact/jarvis#152 + life-theses#11 — neither ever got a sweep row)
# --------------------------------------------------------------------------- #
def test_defaults_name_the_live_post_cutover_repos():
    """Migration guard: the fallback repo set must not name the archived
    pre-cutover repos — a lost config.toml would otherwise sweep dead repos
    and report a permanently quiet day."""
    from gazette.config import DEFAULTS

    assert "dtch1997/jarvis" in DEFAULTS["github_repos"]
    assert "ArcadiaImpact/jarvis" not in DEFAULTS["github_repos"]
    assert "dtch1997/arsenal" not in DEFAULTS["github_repos"]


def test_coverage_owners_defaults_to_swept_owners_and_honors_override():
    from gazette.config import coverage_owners

    cfg = Config(github_repos=["dtch1997/jarvis", "dtch1997/life-theses"])
    assert coverage_owners(cfg) == ["dtch1997"]  # deduped
    cfg2 = Config(github_repos=["dtch1997/jarvis"], watch_owners=["dtch1997", "ArcadiaImpact"])
    assert coverage_owners(cfg2) == ["dtch1997", "ArcadiaImpact"]


def _fake_search(rows_by_label, warn_labels=()):
    def search(owner, label):
        if label in warn_labels:
            return [], f"lane-coverage search ({owner}, {label}): gh failed"
        return list(rows_by_label.get(label, [])), None

    return search


def _stray(repo, number, label, title="a stranded PR"):
    return {"repo": repo, "number": number, "title": title,
            "url": f"https://github.com/{repo}/pull/{number}", "label": label,
            "is_draft": False}


def test_unswept_lane_prs_reports_only_repos_outside_the_sweep(monkeypatch):
    from gazette import gh

    cfg = Config(github_repos=["dtch1997/jarvis"])
    monkeypatch.setattr(gh, "search_lane_prs", _fake_search({
        LABEL_APPROVAL: [
            _stray("dtch1997/jarvis", 29, LABEL_APPROVAL),          # swept — ignored
            _stray("dtch1997/life-theses", 11, LABEL_APPROVAL, "Weekly thesis refresh"),
        ],
        LABEL_DELAY: [_stray("dtch1997/life-theses", 11, LABEL_DELAY)],  # dupe
    }))
    rows, warnings = gh.unswept_lane_prs(cfg)
    assert warnings == []
    assert [(r["repo"], r["number"]) for r in rows] == [("dtch1997/life-theses", 11)]

    msgs = gh.coverage_gap_messages(rows)
    assert "life-theses#11" in msgs[0] and "not in github_repos" in msgs[0]
    assert LABEL_APPROVAL in msgs[0]


def test_unswept_lane_search_failure_is_a_warning_not_a_crash(monkeypatch):
    from gazette import gh
    from gazette.lanes import LANE_LABELS

    cfg = Config(github_repos=["dtch1997/jarvis"])
    monkeypatch.setattr(gh, "search_lane_prs",
                        _fake_search({}, warn_labels=LANE_LABELS))
    rows, warnings = gh.unswept_lane_prs(cfg)
    assert rows == [] and len(warnings) == len(LANE_LABELS)
    assert all("lane-coverage search" in w for w in warnings)


def test_sweep_spools_an_unswept_row_and_reports_it(tmp_path, monkeypatch):
    """The evidence trail the 2026-08-18 investigation lacked: a stranded PR
    now gets a log.jsonl row with action=unswept instead of no row at all."""
    import json

    from gazette import gh, sweep

    monkeypatch.setenv("GAZETTE_HOME", str(tmp_path))
    cfg = Config(github_repos=["dtch1997/jarvis"])
    monkeypatch.setattr(gh, "list_open_prs", lambda repo: ([], [], False))
    monkeypatch.setattr(gh, "unswept_lane_prs",
                        lambda cfg: ([_stray("dtch1997/life-theses", 11, LABEL_APPROVAL)], []))

    report = sweep.run(cfg, now=NOW, dry_run=True)
    assert [r["ref"] for r in report["unswept"]] == ["life-theses#11"]
    assert any("life-theses#11" in w for w in report["warnings"])
    assert "[unswept] life-theses#11" in sweep.format_report(report)

    rows = [json.loads(line) for line in sweep.log_path().read_text().splitlines()]
    assert [(r["ref"], r["action"]) for r in rows] == [("life-theses#11", "unswept")]


def test_coverage_gap_is_an_anomaly_without_marking_the_edition_incomplete():
    """A stranded PR is a real anomaly (nobody will decide it) but the data we
    did collect is complete — so no INCOMPLETE banner, unlike a dead collector."""
    cfg = Config()
    gap = "life-theses#11 carries requires-approval but dtch1997/life-theses is not in github_repos"
    ed = compile_edition(cfg, NOW, [], [], coverage_gaps=[gap])
    assert not ed.incomplete
    assert any("not swept" in a and "life-theses#11" in a for a in ed.anomalies)
    text = build_notes(cfg, ed)
    assert "INCOMPLETE" not in text
    assert "## Anomalies" in text and "life-theses#11" in text


# --------------------------------------------------------------------------- #
# versions: nightly cut / deploy / switch against a real (temp) git repo
# --------------------------------------------------------------------------- #
def _sh(cwd, *args):
    subprocess.run(args, cwd=str(cwd), check=True, capture_output=True, text=True)


@pytest.fixture
def vcfg(tmp_path, monkeypatch):
    """A bare origin + a 'deployed checkout' clone, wired into a Config with
    no deploy_cmds (the venv/cron steps are not under test)."""
    monkeypatch.setenv("GAZETTE_HOME", str(tmp_path))
    origin = tmp_path / "origin.git"
    _sh(tmp_path, "git", "init", "--bare", "-q", "-b", "main", str(origin))
    co = tmp_path / "checkout"
    _sh(tmp_path, "git", "init", "-q", "-b", "main", str(co))
    _sh(co, "git", "config", "user.email", "t@t")
    _sh(co, "git", "config", "user.name", "t")
    (co / "f.txt").write_text("one\n")
    _sh(co, "git", "add", "f.txt")
    _sh(co, "git", "commit", "-qm", "c1")
    _sh(co, "git", "remote", "add", "origin", str(origin))
    _sh(co, "git", "push", "-qu", "origin", "main")
    return Config(checkout=str(co), deploy_cmds=[])


def _commit(cfg, text):
    from pathlib import Path

    co = Path(cfg.checkout)
    (co / "f.txt").write_text(text)
    _sh(co, "git", "commit", "-aqm", text)
    _sh(co, "git", "push", "-q", "origin", "main")


def _head(cfg):
    from gazette.versions import _git, checkout_path

    return _git(checkout_path(cfg), "rev-parse", "HEAD")[1]


def test_next_tag_suffixes_same_day():
    from gazette.versions import _next_tag

    day = datetime(2026, 8, 19)
    assert _next_tag(set(), day) == "v2026.08.19"
    assert _next_tag({"v2026.08.19"}, day) == "v2026.08.19.2"
    assert _next_tag({"v2026.08.19", "v2026.08.19.2"}, day) == "v2026.08.19.3"


def test_cut_tags_origin_main_and_is_idempotent(vcfg):
    from gazette import versions

    ok, msg = versions.cut(vcfg, now=datetime(2026, 8, 19))
    assert ok and "v2026.08.19" in msg
    ok, msg = versions.cut(vcfg, now=datetime(2026, 8, 19))
    assert ok and "nothing to cut" in msg  # same tip → no-op
    _commit(vcfg, "two\n")
    ok, msg = versions.cut(vcfg, now=datetime(2026, 8, 19))
    assert ok and "v2026.08.19.2" in msg  # same day, new tip → suffixed
    rows, warn = versions.list_versions(vcfg)
    assert warn is None
    assert [r["tag"] for r in rows][:2] == ["v2026.08.19.2", "v2026.08.19"]
    # the listed sha is the peeled COMMIT sha, not the annotated tag object
    assert rows[0]["sha"] and _head(vcfg).startswith(rows[0]["sha"])


def test_switch_pins_and_deploys_and_latest_unpins(vcfg):
    from gazette import versions

    versions.cut(vcfg, now=datetime(2026, 8, 19))
    old_head = _head(vcfg)
    _commit(vcfg, "two\n")
    versions.cut(vcfg, now=datetime(2026, 8, 20))

    ok, lines = versions.switch(vcfg, "v2026.08.19")
    assert ok, lines
    assert versions.current_pin() == "v2026.08.19"
    assert _head(vcfg) == old_head  # box rolled back to the old version
    assert "PINNED" in versions.status(vcfg) and "v2026.08.19" in versions.status(vcfg)

    # nightly deploy keeps the pin
    ok, lines = versions.deploy(vcfg)
    assert ok and _head(vcfg) == old_head

    ok, lines = versions.switch(vcfg, "latest")
    assert ok, lines
    assert versions.current_pin() is None
    assert _head(vcfg) != old_head  # back on main's tip
    assert "PINNED" not in versions.status(vcfg)


def test_switch_rejects_unknown_targets(vcfg):
    from gazette import versions

    ok, lines = versions.switch(vcfg, "v2020.01.01")
    assert not ok and "no such version" in lines[0]
    ok, lines = versions.switch(vcfg, "garbage")
    assert not ok and "not a version tag" in lines[0]
    assert versions.current_pin() is None  # failed switches leave no pin


def test_deploy_unpinned_fast_forwards_main(vcfg):
    from gazette import versions
    from gazette.versions import _git, checkout_path

    _commit(vcfg, "two\n")
    new_head = _head(vcfg)
    _sh(checkout_path(vcfg), "git", "reset", "-q", "--hard", "HEAD~1")
    assert _head(vcfg) != new_head
    ok, lines = versions.deploy(vcfg)
    assert ok, lines
    assert _head(vcfg) == new_head
    assert _git(checkout_path(vcfg), "branch", "--show-current")[1] == "main"
