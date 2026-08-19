"""``gazette sweep|notes|status`` — see package docstring for the lane model."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from pathlib import Path

from . import editions, gh, notes as notes_mod, sweep as sweep_mod, synthesize, versions
from .config import load_config


def _flare_warn(body: str) -> None:
    """Best-effort warn flare; a cron must not crash on transport."""
    try:
        import flare

        flare.send(body, sev="warn", source="gazette")
    except Exception as e:
        print(f"[flare failed: {e}]", file=sys.stderr)


def _desk_digest() -> str | None:
    """Fold the desk inbox into the morning edition; None if desk is absent
    or errors (the notes cron must not depend on it)."""
    import shutil

    exe = shutil.which("desk") or (
        str(Path.home() / ".local" / "bin" / "desk")
        if (Path.home() / ".local" / "bin" / "desk").exists()
        else None
    )
    if not exe:
        return None
    try:
        proc = subprocess.run([exe, "digest"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    out = proc.stdout.strip()
    return out if proc.returncode == 0 and out else None


def _collect(cfg):
    """Gather open PRs + recent merges across all repos.

    Returns ``(open_prs, merged, warnings, collector_errors, pr_failed_repos,
    coverage_gaps)``.
    A hard collector failure (gh unreachable) becomes a ``collector_errors``
    entry (→ Anomalies + INCOMPLETE edition), never a silent empty result;
    ``pr_failed_repos`` gates edition-count credit. Soft per-row parse issues
    stay in ``warnings``. ``coverage_gaps`` lists lane-labelled PRs in repos
    that are not configured to be swept at all (see gh.unswept_lane_prs).
    """
    open_prs, merged, warnings, collector_errors, pr_failed_repos = [], [], [], [], []
    since = datetime.now(timezone.utc) - timedelta(hours=cfg.notes_window_hours)
    for repo in cfg.github_repos:
        prs, w, failed = gh.list_open_prs(repo)
        open_prs.extend(prs)
        if failed:
            collector_errors.extend(w)
            pr_failed_repos.append(repo)
        else:
            warnings.extend(w)
        m, w2, failed2 = gh.list_merged_since(repo, since)
        merged.extend(m)
        if failed2:
            collector_errors.extend(w2)
        else:
            warnings.extend(w2)
    strays, stray_warnings = gh.unswept_lane_prs(cfg)
    warnings.extend(stray_warnings)
    coverage_gaps = gh.coverage_gap_messages(strays)
    return open_prs, merged, warnings, collector_errors, pr_failed_repos, coverage_gaps


def cmd_sweep(args) -> int:
    cfg = load_config()
    report = sweep_mod.run(cfg, dry_run=args.dry_run)
    print(sweep_mod.format_report(report))
    return 0


def cmd_notes(args) -> int:
    cfg = load_config()
    now = datetime.now(timezone.utc)
    open_prs, merged, warnings, collector_errors, pr_failed_repos, gaps = _collect(cfg)
    ed = notes_mod.compile_edition(
        cfg, now, open_prs, merged, warnings, collector_errors, gaps
    )
    news = synthesize.synthesize(cfg, merged)
    version_line = versions.status(cfg)
    if version_line.startswith("version status unavailable"):
        version_line = None  # no git checkout here — don't clutter the edition
    text = notes_mod.build_notes(cfg, ed, news=news, desk_text=_desk_digest(),
                                 version_line=version_line)
    path = notes_mod.spool_notes(now, text)
    # Delivery-log integrity: only record a delivered edition when at least one
    # repo's PR collector succeeded — empty refs from a total collector failure
    # are not a genuine "nothing to show".
    if len(pr_failed_repos) < len(cfg.github_repos):
        editions.record_edition(now, ed.visible_refs)
    print(text)
    if path:
        print(f"\n[spooled → {path}]", file=sys.stderr)
    if args.flare:
        try:
            import flare

            sev = "warn" if ed.incomplete else "info"
            flare.send(
                notes_mod.flare_body(ed, news=news, spool_path=path,
                                     version_line=version_line),
                sev=sev, source="gazette",
            )
        except Exception as e:  # a notes cron must not crash on transport
            print(f"[flare failed: {e}]", file=sys.stderr)
    return 0


def cmd_version(args) -> int:
    cfg = load_config()
    if args.version_cmd == "cut":
        ok, msg = versions.cut(cfg)
        print(msg)
        if not ok:
            _flare_warn(f"gazette version cut failed:\n• {msg}")
        return 0 if ok else 1
    if args.version_cmd == "deploy":
        ok, lines = versions.deploy(cfg)
        print("\n".join(lines))
        if not ok:
            _flare_warn("gazette version deploy failed:\n" +
                        "\n".join(f"• {l}" for l in lines[-3:]))
        return 0 if ok else 1
    if args.version_cmd == "switch":
        ok, lines = versions.switch(cfg, args.target)
        print("\n".join(lines))
        return 0 if ok else 1
    if args.version_cmd == "list":
        rows, warn = versions.list_versions(cfg, limit=args.n)
        if warn:
            print(warn, file=sys.stderr)
            return 1
        pin = versions.current_pin()
        for r in rows:
            marker = "  ← pinned" if r["tag"] == pin else ""
            print(f"{r['tag']}  {r['sha']}  {r['date']}{marker}")
        if not rows:
            print("no versions cut yet — the nightly deploy cron cuts the first one")
        return 0
    print(versions.status(cfg))  # status (default)
    return 0


def cmd_status(args) -> int:
    cfg = load_config()
    now = datetime.now(timezone.utc)
    open_prs, merged, _, _, _, _ = _collect(cfg)
    print(notes_mod.digest(cfg, now, open_prs, merged))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gazette", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sweep = sub.add_parser("sweep", help="hourly merge pass over all configured repos")
    p_sweep.add_argument("--dry-run", action="store_true", help="decide and report, merge nothing")
    p_sweep.set_defaults(fn=cmd_sweep)

    p_ver = sub.add_parser("version", help="nightly versions: cut/deploy/switch/list/status")
    ver_sub = p_ver.add_subparsers(dest="version_cmd", required=True)
    ver_sub.add_parser("cut", help="tag origin/main tip as tonight's vYYYY.MM.DD and push")
    ver_sub.add_parser("deploy", help="deploy the pin (or main's nightly state) + run deploy_cmds")
    p_switch = ver_sub.add_parser("switch", help="pin the box to a version tag, or 'latest' to unpin")
    p_switch.add_argument("target", help="a version tag (v2026.08.19) or 'latest'")
    p_list = ver_sub.add_parser("list", help="recent versions, newest first")
    p_list.add_argument("-n", type=int, default=15, help="how many to show")
    ver_sub.add_parser("status", help="what the box is running + pin state")
    p_ver.set_defaults(fn=cmd_version)

    p_notes = sub.add_parser("notes", help="render morning patch notes (spooled to ~/.gazette/notes/)")
    p_notes.add_argument("--flare", action="store_true", help="also send the digest via flare")
    p_notes.set_defaults(fn=cmd_notes)

    p_status = sub.add_parser("status", help="one-line digest")
    p_status.set_defaults(fn=cmd_status)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
