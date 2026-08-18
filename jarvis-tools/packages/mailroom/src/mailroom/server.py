from __future__ import annotations
import http.server,socket,threading
from dataclasses import dataclass
from .dashboard import render_html
def _port():
    with socket.socket() as s:s.bind(("127.0.0.1",0));return s.getsockname()[1]
@dataclass
class Server:
    local_url:str; url:str; httpd:object; hub_name:str|None=None
    @property
    def alive(self):return True
    def stop(self):
        if self.hub_name:
            try:
                import lobby;lobby.unregister(self.hub_name)
            except Exception:pass
        self.httpd.shutdown();self.httpd.server_close()
def serve(port=None,tunnel=True):
    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self,*a):pass
        def do_GET(self):
            b=render_html().encode();self.send_response(200);self.send_header("Content-Type","text/html;charset=utf-8");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
    port=port or _port(); h=http.server.ThreadingHTTPServer(("127.0.0.1",port),H);threading.Thread(target=h.serve_forever,daemon=True).start(); local=f"http://127.0.0.1:{port}"; s=Server(local,local,h)
    if tunnel:
        try:
            import lobby;s.url=lobby.serve(port,name="mailroom",kind="mailroom",title="mailroom — thought capture");s.hub_name="mailroom"
        except Exception:pass
    return s
