"""``mailroom serve`` — serve the digest through the shared lobby hub,
re-rendering on an interval. Falls back to plain localhost (with a printed
notice) if lobby is unavailable, exactly as threads/databrowser/desk degrade.
"""

from __future__ import annotations

import http.server
import socket
import sys
import threading
from dataclasses import dataclass, field

from . import digest


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@dataclass
class MailroomServer:
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
          ) -> MailroomServer:
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            try:
                html = digest.render_html(refresh=interval)
            except Exception as e:
                html = f"<pre>render error: {e}</pre>"
            payload = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    port = port or _free_port()
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    local_url = f"http://127.0.0.1:{port}"
    srv = MailroomServer(local_url=local_url, url=local_url, httpd=httpd)

    if not tunnel:
        return srv
    try:
        import lobby
        public_url = lobby.serve(port, name="mailroom", kind="mailroom",
                                 title="mailroom — thought-capture digest")
        srv.url = public_url
        srv.hub_name = public_url.rstrip("/").rsplit("/a/", 1)[-1]
    except Exception as e:
        print(f"note: lobby hub unavailable ({e}); serving locally only.",
              file=sys.stderr)
    return srv
