"""Serve a ledger's gallery over local HTTP + the shared lobby tunnel.

Unlike databrowser this is not a static site: claim edits and status
toggles POST back and rewrite cards.jsonl, so the server is a small
stdlib handler run as `python -m curator.server <ledger> <port>`. The
service model mirrors databrowser: the process is launched detached, a
Viewer with the public URL comes back, and the lobby hub provides the
one tunnel + index page (local-only fallback if the hub is unreachable).
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Union

from .core import Ledger

_GALLERY_HTML = Path(__file__).with_name("gallery.html")

_CONTENT_TYPES = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml", ".gif": "image/gif", ".webp": "image/webp",
}


class _Handler(BaseHTTPRequestHandler):
    ledger: Ledger  # set on the server class by run()

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj).encode(), "application/json")

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send(200, _GALLERY_HTML.read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/cards":
            self._json(200, [c.to_dict() for c in self.ledger.cards()])
        elif path.startswith("/figures/"):
            name = Path(path).name  # flat dir; strips any traversal
            fp = self.ledger.figures_dir / name
            if fp.is_file():
                ctype = _CONTENT_TYPES.get(fp.suffix.lower(), "application/octet-stream")
                self._send(200, fp.read_bytes(), ctype)
            else:
                self._json(404, {"error": f"no figure {name}"})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if not path.startswith("/api/cards/"):
            self._json(404, {"error": "not found"})
            return
        card_id = Path(path).name
        try:
            length = int(self.headers.get("Content-Length", 0))
            fields = json.loads(self.rfile.read(length) or b"{}")
            card = self.ledger.update(card_id, **fields)
        except KeyError as e:
            self._json(404, {"error": str(e)})
        except (ValueError, json.JSONDecodeError) as e:
            self._json(400, {"error": str(e)})
        else:
            self._json(200, card.to_dict())

    def log_message(self, *args) -> None:  # keep the detached process quiet
        pass


def run(root: Union[str, Path], port: int) -> None:
    """Serve `root` on 127.0.0.1:port, blocking. The in-process entrypoint;
    `serve()` runs this detached."""
    server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    _Handler.ledger = Ledger(root)
    server.serve_forever()


# -- the databrowser service model: detached process + lobby ---------------


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_port(port: int, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.1)
    return False


def _pid_alive(pid: Union[int, None]) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        if stat.rsplit(")", 1)[1].split()[0] == "Z":
            return False
    except OSError:
        pass
    return True


@dataclass
class Viewer:
    """Handle to a running gallery. Call :meth:`stop` when done."""

    url: str
    local_url: str
    root: Path
    http_pid: Union[int, None] = None
    hub_name: Union[str, None] = None

    @property
    def alive(self) -> bool:
        return _pid_alive(self.http_pid)

    def stop(self) -> None:
        if self.hub_name:
            try:
                import lobby

                lobby.unregister(self.hub_name)
            except Exception:
                pass  # hub gone — nothing to clean
        if _pid_alive(self.http_pid):
            try:
                os.killpg(os.getpgid(self.http_pid), signal.SIGTERM)
            except OSError:
                try:
                    os.kill(self.http_pid, signal.SIGTERM)
                except OSError:
                    pass
            try:
                os.waitpid(self.http_pid, os.WNOHANG)
            except OSError:
                pass


def serve(
    root: Union[str, Path, None] = None,
    *,
    name: Union[str, None] = None,
    port: Union[int, None] = None,
    tunnel: bool = True,
) -> Viewer:
    """Serve the ledger at ``root`` (default resolution as :class:`Ledger`)
    and return a :class:`Viewer` with the public URL."""
    ledger = Ledger(root)
    if not ledger.cards_path.is_file():
        raise FileNotFoundError(
            f"no ledger at {ledger.root} (expected {ledger.cards_path}) — "
            "curator.add() something first"
        )
    port = port or _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "curator.server", str(ledger.root.resolve()), str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    local_url = f"http://127.0.0.1:{port}"
    if not _wait_port(port):
        proc.terminate()
        raise RuntimeError(f"gallery server failed to start on port {port}")

    if not tunnel:
        return Viewer(url=local_url, local_url=local_url, root=ledger.root, http_pid=proc.pid)

    import lobby

    name = name or f"curator-{ledger.root.resolve().name}"
    try:
        public_url = lobby.serve(
            port, name=name, kind="curator", title=f"gallery: {ledger.root.resolve()}",
            pid=proc.pid, cwd=str(ledger.root.resolve()),
        )
    except Exception as e:
        print(f"note: lobby hub unavailable ({e}); serving locally only.", file=sys.stderr)
        return Viewer(url=local_url, local_url=local_url, root=ledger.root, http_pid=proc.pid)
    hub_name = public_url.rstrip("/").rsplit("/a/", 1)[-1]
    return Viewer(url=public_url, local_url=local_url, root=ledger.root,
                  http_pid=proc.pid, hub_name=hub_name)


if __name__ == "__main__":
    run(sys.argv[1], int(sys.argv[2]))
