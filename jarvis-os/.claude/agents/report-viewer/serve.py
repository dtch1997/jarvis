#!/usr/bin/env python3
"""
report-viewer driver: serve a local report over a Cloudflare quick tunnel.

Subcommands
-----------
  serve <path> [--slug S] [--title T]   start a viewer, print the public URL
  list                                   show active viewers
  stop <slug> | stop --all               tear a viewer (or all) down

Design
------
The HTTP server (`python3 -m http.server`) and the tunnel (`cloudflared
tunnel --url ...`) must OUTLIVE this driver so the user keeps viewing after
the subagent returns. We launch both with `start_new_session=True` (the
subprocess equivalent of setsid) so they detach into their own session and
survive this process exiting. This driver itself runs in the FOREGROUND and
returns fast — as soon as the trycloudflare URL appears — so the caller gets
one clean completion, not a process held open forever.

This is the intended inverse of the "background job" anti-pattern: we are
standing up a persistent *service*, not waiting on a job to finish, so
detaching is correct. Teardown is explicit (`stop`), recorded per-slug in a
state file, so nothing is ever orphaned silently.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE_DIR = HERE / "state"
URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
URL_WAIT_SECS = 40


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "-", text).strip("-").lower()
    return s or "report"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def _state_path(slug: str) -> Path:
    return STATE_DIR / f"{slug}.json"


def _load_state(slug: str) -> dict | None:
    p = _state_path(slug)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _all_states() -> list[dict]:
    if not STATE_DIR.exists():
        return []
    out = []
    for p in sorted(STATE_DIR.glob("*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except Exception:
            continue
    return out


def _die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------- #
# markdown -> styled standalone HTML
# --------------------------------------------------------------------------- #
_CSS = """
:root { color-scheme: light dark; }
body { max-width: 860px; margin: 2.5rem auto; padding: 0 1.2rem;
  font: 16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
  color: #1f2328; background: #fff; }
@media (prefers-color-scheme: dark) { body { color: #e6edf3; background: #0d1117; }
  a { color: #4493f8; } pre, code { background: #161b22 !important; }
  table th, table td { border-color: #30363d; } hr { background: #30363d; } }
h1,h2,h3,h4 { line-height: 1.25; margin-top: 1.8rem; }
h1,h2 { border-bottom: 1px solid #d0d7de; padding-bottom: .3rem; }
a { color: #0969da; }
code { background: #f6f8fa; padding: .15em .35em; border-radius: 5px; font-size: 85%; }
pre { background: #f6f8fa; padding: 1rem; border-radius: 8px; overflow: auto; }
pre code { background: none; padding: 0; font-size: 90%; }
table { border-collapse: collapse; margin: 1rem 0; }
table th, table td { border: 1px solid #d0d7de; padding: .4rem .8rem; }
blockquote { margin: 0; padding: 0 1rem; color: #656d76; border-left: .25rem solid #d0d7de; }
img { max-width: 100%; }
hr { border: 0; height: 1px; background: #d0d7de; }
.codehilite { border-radius: 8px; }
"""

_HTML_TMPL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{css}</style></head>
<body>{body}</body></html>
"""


def render_markdown(md_text: str, title: str) -> str:
    import markdown  # available in this env (py-markdown + pygments)

    body = markdown.markdown(
        md_text,
        extensions=["extra", "tables", "fenced_code", "codehilite", "sane_lists", "toc"],
        extension_configs={"codehilite": {"guess_lang": False}},
    )
    try:
        from pygments.formatters import HtmlFormatter

        pyg_css = HtmlFormatter().get_style_defs(".codehilite")
    except Exception:
        pyg_css = ""
    return _HTML_TMPL.format(title=title, css=_CSS + "\n" + pyg_css, body=body)


# --------------------------------------------------------------------------- #
# serve
# --------------------------------------------------------------------------- #
def cmd_serve(args: argparse.Namespace) -> None:
    if not shutil.which("cloudflared"):
        _die("cloudflared not found on PATH. Install it before serving.")

    src = Path(args.path).expanduser().resolve()
    if not src.exists():
        _die(f"path does not exist: {src}")

    slug = _slugify(args.slug) if args.slug else _slugify(src.stem)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # If a viewer with this slug is already live, refuse (multiple-viewer model:
    # the caller should pick a distinct slug, or stop the old one first).
    existing = _load_state(slug)
    if existing and (_pid_alive(existing.get("tunnel_pid")) or _pid_alive(existing.get("server_pid"))):
        _die(
            f"a viewer named '{slug}' is already live at {existing.get('url')}.\n"
            f"  reuse it, or `serve.py stop {slug}` first, or pass a different --slug."
        )

    # Decide the directory we actually serve.
    if src.is_dir():
        serve_dir = src
        entry = "index.html" if (src / "index.html").exists() else ""
    elif src.suffix.lower() in (".md", ".markdown"):
        # Render markdown into a per-slug render dir, copy sibling assets so
        # relative image/links keep working.
        render_dir = STATE_DIR / f"{slug}.render"
        if render_dir.exists():
            shutil.rmtree(render_dir)
        render_dir.mkdir(parents=True)
        title = args.title or src.stem
        html = render_markdown(src.read_text(encoding="utf-8", errors="replace"), title)
        (render_dir / "index.html").write_text(html, encoding="utf-8")
        for sib in src.parent.iterdir():
            if sib.is_file() and sib.suffix.lower() in (
                ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js",
            ):
                try:
                    shutil.copy2(sib, render_dir / sib.name)
                except Exception:
                    pass
        serve_dir = render_dir
        entry = "index.html"
    else:
        # A single non-markdown file (e.g. report.html): serve its parent dir,
        # link straight to the file.
        serve_dir = src.parent
        entry = src.name

    port = args.port or _free_port()
    log_path = STATE_DIR / f"{slug}.cloudflared.log"
    srv_log_path = STATE_DIR / f"{slug}.http.log"

    # 1) HTTP server, detached so it outlives this driver.
    srv_log = open(srv_log_path, "wb")
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1",
         "--directory", str(serve_dir)],
        stdout=srv_log, stderr=subprocess.STDOUT, start_new_session=True,
    )

    # 2) Cloudflare quick tunnel, detached likewise. URL is parsed from its log.
    log = open(log_path, "wb")
    tunnel = subprocess.Popen(
        ["cloudflared", "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )

    # 3) Poll the tunnel log for the public URL.
    url = None
    deadline = time.time() + URL_WAIT_SECS
    while time.time() < deadline:
        if tunnel.poll() is not None:
            break
        try:
            m = URL_RE.search(log_path.read_text(errors="replace"))
        except Exception:
            m = None
        if m:
            url = m.group(0)
            break
        time.sleep(0.5)

    if not url:
        # Clean up the half-built viewer rather than leaking processes.
        for p in (tunnel, server):
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            except Exception:
                pass
        tail = ""
        try:
            tail = log_path.read_text(errors="replace")[-600:]
        except Exception:
            pass
        _die(f"tunnel did not produce a URL within {URL_WAIT_SECS}s.\n--- cloudflared log tail ---\n{tail}")

    full_url = url + ("/" + entry if entry else "/")
    state = {
        "slug": slug,
        "url": url,
        "full_url": full_url,
        "port": port,
        "server_pid": server.pid,
        "tunnel_pid": tunnel.pid,
        "source": str(src),
        "serve_dir": str(serve_dir),
        "entry": entry,
        "started_at": _now(),
        "cloudflared_log": str(log_path),
    }
    _state_path(slug).write_text(json.dumps(state, indent=2))

    print(f"slug:      {slug}")
    print(f"serving:   {src}")
    print(f"local:     http://127.0.0.1:{port}/{entry}")
    print(f"PUBLIC:    {full_url}")
    print(f"teardown:  {sys.executable} {__file__} stop {slug}")


# --------------------------------------------------------------------------- #
# list / stop
# --------------------------------------------------------------------------- #
def cmd_list(_args: argparse.Namespace) -> None:
    states = _all_states()
    if not states:
        print("no viewers recorded.")
        return
    for st in states:
        flag = "LIVE" if _is_alive(st) else "dead"
        print(f"[{flag}] {st['slug']:<24} {st.get('full_url','?')}")
        print(f"        source: {st.get('source','?')}  started: {st.get('started_at','?')}")


def _teardown(st: dict) -> None:
    for key in ("tunnel_pid", "server_pid"):
        pid = st.get(key)
        if not _pid_alive(pid):
            continue
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
    # remove state + render dir + logs
    slug = st.get("slug", "")
    if slug:
        for p in (
            _state_path(slug),
            STATE_DIR / f"{slug}.cloudflared.log",
            STATE_DIR / f"{slug}.http.log",
        ):
            p.unlink(missing_ok=True)
        rd = STATE_DIR / f"{slug}.render"
        if rd.exists():
            shutil.rmtree(rd, ignore_errors=True)


def _is_alive(st: dict) -> bool:
    return _pid_alive(st.get("tunnel_pid")) and _pid_alive(st.get("server_pid"))


def cmd_prune(_args: argparse.Namespace) -> None:
    """Reap only dead/stale viewers; leave live ones untouched."""
    dead = [st for st in _all_states() if not _is_alive(st)]
    if not dead:
        print("nothing to prune (no dead viewers).")
        return
    for st in dead:
        _teardown(st)
        print(f"pruned {st.get('slug')}")


def cmd_stop(args: argparse.Namespace) -> None:
    if args.all:
        states = _all_states()
        if not states:
            print("no viewers to stop.")
            return
        for st in states:
            _teardown(st)
            print(f"stopped {st.get('slug')}")
        return
    if not args.slug:
        _die("stop needs a <slug> or --all")
    st = _load_state(args.slug)
    if not st:
        _die(f"no viewer named '{args.slug}' (try `list`)")
    _teardown(st)
    print(f"stopped {args.slug}")


def main() -> None:
    ap = argparse.ArgumentParser(description="serve a report over a Cloudflare quick tunnel")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("serve", help="start a viewer")
    sp.add_argument("path", help="report file (.html/.md) or directory")
    sp.add_argument("--slug", help="name for this viewer (default: from filename)")
    sp.add_argument("--title", help="title for rendered markdown")
    sp.add_argument("--port", type=int, help="local port (default: random free port)")
    sp.set_defaults(func=cmd_serve)

    lp = sub.add_parser("list", help="list active viewers")
    lp.set_defaults(func=cmd_list)

    pp = sub.add_parser("prune", help="tear down only dead/stale viewers, keep live ones")
    pp.set_defaults(func=cmd_prune)

    stp = sub.add_parser("stop", help="tear down a viewer")
    stp.add_argument("slug", nargs="?", help="viewer slug")
    stp.add_argument("--all", action="store_true", help="stop every viewer")
    stp.set_defaults(func=cmd_stop)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
