from datetime import datetime, timedelta, timezone

import pytest

from gazette.config import Config
from gazette.lanes import (
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
        labels=[LABEL_AUTO],
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
# lane resolution
# --------------------------------------------------------------------------- #
def test_lane_labels_respected():
    cfg = Config()
    assert resolve_lane([LABEL_AUTO], ["docs/a.md"], cfg)[0] is Lane.AUTO
    assert resolve_lane([LABEL_DELAY], ["docs/a.md"], cfg)[0] is Lane.DELAY
    assert resolve_lane([LABEL_BLOCKED], ["docs/a.md"], cfg)[0] is Lane.BLOCKED


def test_unlabeled_defaults_to_delay_with_reason():
    lane, reasons = resolve_lane([], ["docs/a.md"], Config())
    assert lane is Lane.DELAY
    assert any("unclassified" in r for r in reasons)


def test_auto_demoted_on_protected_paths():
    lane, reasons = resolve_lane([LABEL_AUTO], ["CLAUDE.md"], Config())
    assert lane is Lane.DELAY
    assert any("demoted to delay" in r for r in reasons)


def test_credential_paths_demote_to_blocked_regardless_of_label():
    for labels in ([LABEL_AUTO], [LABEL_DELAY], []):
        lane, reasons = resolve_lane(labels, ["conf/.env.prod"], Config())
        assert lane is Lane.BLOCKED
        assert any("demoted to blocked" in r for r in reasons)


# --------------------------------------------------------------------------- #
# merge decisions
# --------------------------------------------------------------------------- #
def test_auto_green_merges():
    assert decide(make_pr(), Config(), NOW).action == "merge"


def test_draft_and_veto_and_changes_requested_skip():
    cfg = Config()
    assert decide(make_pr(is_draft=True), cfg, NOW).action == "skip"
    assert decide(make_pr(labels=[LABEL_AUTO, LABEL_VETO]), cfg, NOW).action == "skip"
    assert decide(make_pr(review_decision="CHANGES_REQUESTED"), cfg, NOW).action == "skip"


def test_failing_or_pending_checks_wait():
    cfg = Config()
    d = decide(make_pr(checks="failing"), cfg, NOW)
    assert d.action == "wait" and "checks failing" in d.anomalies
    assert decide(make_pr(checks="pending"), cfg, NOW).action == "wait"


def test_delay_lane_wall_clock_fallback():
    # with no edition data (appearances=None) the old wall-clock window applies
    cfg = Config(delay_hours=36)
    young = make_pr(labels=[LABEL_DELAY], created_at=NOW - timedelta(hours=10))
    old = make_pr(labels=[LABEL_DELAY], created_at=NOW - timedelta(hours=40))
    assert decide(young, cfg, NOW).action == "wait"
    assert decide(old, cfg, NOW).action == "merge"


def test_delay_lane_counts_editions_not_hours():
    cfg = Config(delay_hours=36, delay_editions=2)
    pr = make_pr(labels=[LABEL_DELAY], created_at=NOW - timedelta(hours=60))
    d = decide(pr, cfg, NOW, appearances=1)
    assert d.action == "wait" and "1/2" in d.reason  # 60h old but only 1 edition
    assert decide(pr, cfg, NOW, appearances=2).action == "merge"


def test_delay_lane_stall_anomaly_when_editions_never_arrive():
    cfg = Config(delay_hours=36, delay_editions=2)
    pr = make_pr(labels=[LABEL_DELAY], created_at=NOW - timedelta(hours=120))
    d = decide(pr, cfg, NOW, appearances=0)
    assert d.action == "wait"
    assert any("notes cron" in a for a in d.anomalies)


def test_blocked_never_merges():
    pr = make_pr(labels=[LABEL_BLOCKED], created_at=NOW - timedelta(days=30))
    assert decide(pr, Config(), NOW).action == "skip"


# --------------------------------------------------------------------------- #
# notes rendering
# --------------------------------------------------------------------------- #
MERGED_ROW = {
    "repo": "ArcadiaImpact/jarvis", "number": 140, "title": "draft doc",
    "url": "u", "merged_at": NOW - timedelta(hours=3), "author": "agent",
    "labels": [LABEL_AUTO],
}


def _edition(appearances=None):
    cfg = Config()
    open_prs = [
        make_pr(number=141, title="CLAUDE.md tweak", labels=[LABEL_DELAY],
                created_at=NOW - timedelta(hours=5), files=["CLAUDE.md"]),
        make_pr(number=37, title="needs creds", labels=[LABEL_BLOCKED]),
    ]
    return cfg, open_prs, compile_edition(cfg, NOW, open_prs, [MERGED_ROW], appearances)


def test_notes_needs_you_first_with_default_outcomes():
    cfg, open_prs, ed = _edition(appearances={"jarvis#141": 1})
    text = build_notes(cfg, ed)
    assert text.index("## Needs you (2)") < text.index("## News")
    assert "jarvis#141" in text and "unless vetoed" in text and "--add-label veto" in text
    assert "jarvis#37" in text and "sits until you act" in text
    assert "jarvis#140" in text and "(auto)" not in text  # merged list drops lane tags
    assert sorted(ed.visible_refs) == ["jarvis#141", "jarvis#37"]
    d = digest(cfg, NOW, open_prs, [MERGED_ROW])
    assert "merged 1" in d and "1 in pipeline" in d and "1 waiting on you" in d


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

    _, _, busy = _edition(appearances={"jarvis#141": 2})
    body = flare_body(busy, spool_path="/spool/x.md")
    assert body.splitlines()[0].startswith("☀️")
    assert "NEEDS YOU (2)" in body and "merges tonight" in body
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
    delay_pr = make_pr(repo="dtch1997/arsenal", number=37, title="ok repo",
                       labels=[LABEL_DELAY], created_at=NOW - timedelta(hours=5))
    ed = compile_edition(cfg, NOW, [delay_pr], [], appearances={"arsenal#37": 1},
                         collector_errors=[COLLECTOR_ERR])
    assert ed.incomplete and ed.visible_refs == ["arsenal#37"]
    text = build_notes(cfg, ed)
    assert "INCOMPLETE" in text and "arsenal#37" in text
    assert "arsenal#37" in flare_body(ed)  # reachable needs-you still flared


# --------------------------------------------------------------------------- #
# edition-count integrity: a failed collector earns no edition credit (b3)
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
    empty-refs-from-failure must not accrue veto-window credit — and the flare
    goes out --sev warn."""
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
    """(b3): a reachable repo's PRs still earn edition credit; the failed
    repo's PRs (none collected) do not appear in editions.jsonl."""
    from gazette import editions

    repos = Config().github_repos
    ok_pr = make_pr(repo=repos[1], number=37, title="reachable",
                    labels=[LABEL_DELAY], created_at=NOW - timedelta(hours=5))
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
        LABEL_AUTO: [
            _stray("dtch1997/jarvis", 29, LABEL_AUTO),          # swept — ignored
            _stray("dtch1997/life-theses", 11, LABEL_AUTO, "Weekly thesis refresh"),
        ],
        LABEL_DELAY: [_stray("dtch1997/life-theses", 11, LABEL_DELAY)],  # dupe
    }))
    rows, warnings = gh.unswept_lane_prs(cfg)
    assert warnings == []
    assert [(r["repo"], r["number"]) for r in rows] == [("dtch1997/life-theses", 11)]

    msgs = gh.coverage_gap_messages(rows)
    assert "life-theses#11" in msgs[0] and "not in github_repos" in msgs[0]
    assert LABEL_AUTO in msgs[0]


def test_unswept_lane_search_failure_is_a_warning_not_a_crash(monkeypatch):
    from gazette import gh

    cfg = Config(github_repos=["dtch1997/jarvis"])
    monkeypatch.setattr(gh, "search_lane_prs",
                        _fake_search({}, warn_labels=(LABEL_AUTO, LABEL_DELAY, LABEL_BLOCKED)))
    rows, warnings = gh.unswept_lane_prs(cfg)
    assert rows == [] and len(warnings) == 3
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
                        lambda cfg: ([_stray("dtch1997/life-theses", 11, LABEL_AUTO)], []))

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
    gap = "life-theses#11 carries lane:auto but dtch1997/life-theses is not in github_repos"
    ed = compile_edition(cfg, NOW, [], [], coverage_gaps=[gap])
    assert not ed.incomplete
    assert any("not swept" in a and "life-theses#11" in a for a in ed.anomalies)
    text = build_notes(cfg, ed)
    assert "INCOMPLETE" not in text
    assert "## Anomalies" in text and "life-theses#11" in text
