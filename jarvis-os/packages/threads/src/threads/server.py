"""``threads serve`` — serve the dashboard through the shared lobby hub,
re-rendering on an interval. Falls back to a plain localhost HTTP server (with a
printed notice) if lobby is unavailable, exactly as databrowser/desk degrade.
"""

from __future__ import annotations

import http.server
import json
import socket
import sys
import threading
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlsplit

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
    """Serve the dashboard, rebuilding the model every ``interval`` seconds.

    Each request renders from the cached model with *its own* query params
    (``?sort=…&active_days=…&dormant=1&q=…``), and the page carries a meta
    refresh back to the same URL so the sort/filter selection stays sticky
    across the auto-refresh."""
    cache = {"model": dashboard.build()}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def do_GET(self):
            query = parse_qs(urlsplit(self.path).query)
            params = dashboard.params_from_query(query)
            try:
                html = dashboard.render_html(
                    cache["model"], params=params, refresh=interval)
            except Exception as e:  # never 500 the page over a render bug
                html = f"<pre>render error: {e}</pre>"
            payload = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

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
            """
            from .launch import accept, detach, merge_into
            try:
                size = int(self.headers.get("Content-Length", "0") or 0)
                data = json.loads(self.rfile.read(size) or b"{}")
                path = urlsplit(self.path).path.rstrip("/")
                if path.endswith("/launch"):
                    rec = accept(str(data.get("text") or ""),
                                 mode=str(data.get("mode") or "full-auto"),
                                 slug=data.get("slug"))
                    cache["model"] = dashboard.build()  # optimistic render
                    self._json(202, rec)
                elif path.endswith("/detach"):
                    self._json(200, detach(str(data["id"])))
                elif path.endswith("/merge"):
                    self._json(200, merge_into(str(data["id"]), str(data["slug"])))
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
            title="threads — activity dashboard",
        )
        srv.url = public_url
        srv.hub_name = public_url.rstrip("/").rsplit("/a/", 1)[-1]
    except Exception as e:
        print(f"note: lobby hub unavailable ({e}); serving locally only.",
              file=sys.stderr)
    return srv
