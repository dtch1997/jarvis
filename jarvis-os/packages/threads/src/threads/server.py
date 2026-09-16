"""``threads serve`` — serve the thread board through the shared lobby hub,
re-rendering on an interval. Falls back to a plain localhost HTTP server (with a
printed notice) if lobby is unavailable, exactly as databrowser/desk degrade.

Routes:

* ``GET  /``           — the **thread board** (Prompt | Goal | Status): default page
* ``GET  /dashboard``  — the observational activity dashboard (secondary)
* ``GET  /tail?tid=``  — the tail of one executor's newest attempt log
* ``POST /launch``     — accept an intent (durable <100ms, async route/spawn)
* ``POST /goal``       — edit a row's Goal cell (pre-spawn re-derives the gate)
* ``POST /detach``, ``POST /merge``, ``POST /candidate-delete`` — veto affordances

The expensive part of a render (the dashboard model) is cached and refreshed on
an interval; the board re-reads the cheap launcher spool on every request, so a
row added a moment ago is on the page immediately. No request makes a model
call.
"""

from __future__ import annotations

import http.server
import json
import socket
import sys
import threading
from dataclasses import dataclass, field
from html import escape
from urllib.parse import parse_qs, urlsplit

from . import board as board_mod
from . import dashboard


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@dataclass
class ThreadsServer:
    local_url: str
    url: str
    httpd: http.server.ThreadingHTTPServer
    _stop: threading.Event = field(default_factory=threading.Event)
    hub_name: str | None = None

    @property
    def alive(self) -> bool:
        return not self._stop.is_set()

    def stop(self) -> None:
        self._stop.set()
        if self.hub_name:
            try:
                import lobby
                lobby.unregister(self.hub_name)
            except Exception:
                pass
        self.httpd.shutdown()
        self.httpd.server_close()


def serve(*, interval: int = 60, port: int | None = None, tunnel: bool = True
          ) -> ThreadsServer:
    """Serve the board (and the dashboard behind it), rebuilding the dashboard
    model every ``interval`` seconds.

    Each dashboard request renders from the cached model with *its own* query
    params (``?sort=…&active_days=…&dormant=1&q=…``), and the page carries a
    meta refresh back to the same URL so the sort/filter selection stays sticky
    across the auto-refresh."""
    cache = {"model": dashboard.build()}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _html(self, body: str, status: int = 200):
            payload = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            split = urlsplit(self.path)
            path = split.path.rstrip("/")
            query = parse_qs(split.query)
            try:
                if path.endswith("/dashboard"):
                    params = dashboard.params_from_query(query)
                    html = dashboard.render_html(
                        cache["model"], params=params, refresh=interval)
                elif path.endswith("/tail"):
                    tid = (query.get("tid") or [""])[0]
                    html = ("<!doctype html><meta charset='utf-8'>"
                            f"<title>log tail {tid}</title>"
                            "<body style='background:#111;color:#ddd'>"
                            f"<pre style='white-space:pre-wrap'>"
                            f"{escape(board_mod.log_tail(tid))}</pre>")
                else:
                    # the board is the default page (thread-board.md DoD 5).
                    try:
                        from .sessions import open_sessions
                        live = open_sessions()
                    except Exception:  # noqa: BLE001
                        live = None
                    html = board_mod.render_html(
                        board_mod.build(dash=cache["model"]), refresh=interval,
                        open_sessions=live)
            except Exception as e:  # never 500 the page over a render bug
                html = f"<pre>render error: {type(e).__name__}: {e}</pre>"
            self._html(html)

        def _json(self, status: int, body: dict):
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self):
            """``/launch`` (accept + async route/spawn), ``/detach``, ``/merge``.

            ``/launch`` returns the receipt in <100ms; routing and spawning run
            in the detached processor accept() enqueues — never on this thread.
            ``/goal`` is the board's inline Goal edit: pre-spawn it re-derives
            the gate the executor gets, post-spawn it lands as a ``pool.msg``.
            """
            from .launch import accept, detach, merge_into, set_goal
            try:
                size = int(self.headers.get("Content-Length", "0") or 0)
                data = json.loads(self.rfile.read(size) or b"{}")
                path = urlsplit(self.path).path.rstrip("/")
                if path.endswith("/launch"):
                    # accept only: the durable record is written here (<100ms,
                    # no model), and the board re-reads the spool on the next
                    # GET, so the row is real without rebuilding the dashboard.
                    rec = accept(str(data.get("text") or ""),
                                 mode=str(data.get("mode") or "full-auto"),
                                 slug=data.get("slug"))
                    self._json(202, rec)
                elif path.endswith("/goal"):
                    self._json(200, set_goal(str(data["id"]),
                                             str(data.get("goal") or "")))
                elif path.endswith("/detach"):
                    self._json(200, detach(str(data["id"])))
                elif path.endswith("/merge"):
                    self._json(200, merge_into(str(data["id"]), str(data["slug"])))
                elif path.endswith("/candidate-delete"):
                    self._json(200, board_mod.delete_candidate(str(data["slug"])))
                else:
                    self._json(404, {"error": "not found"})
            except (ValueError, KeyError, json.JSONDecodeError) as e:
                self._json(400, {"error": str(e)})
            except Exception as e:  # never 500 the process over a handler bug
                self._json(500, {"error": str(e)})

    port = port or _free_port()
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    local_url = f"http://127.0.0.1:{port}"
    srv = ThreadsServer(local_url=local_url, url=local_url, httpd=httpd)

    def _loop():
        while not srv._stop.wait(interval):
            try:
                cache["model"] = dashboard.build()
            except Exception as e:  # never let the refresh thread kill serving
                print(f"threads: re-render failed ({e})", file=sys.stderr)

    threading.Thread(target=_loop, daemon=True).start()

    if not tunnel:
        return srv
    try:
        import lobby
        public_url = lobby.serve(
            port, name="threads", kind="threads",
            title="threads — board",
        )
        srv.url = public_url
        srv.hub_name = public_url.rstrip("/").rsplit("/a/", 1)[-1]
    except Exception as e:
        print(f"note: lobby hub unavailable ({e}); serving locally only.",
              file=sys.stderr)
    return srv
