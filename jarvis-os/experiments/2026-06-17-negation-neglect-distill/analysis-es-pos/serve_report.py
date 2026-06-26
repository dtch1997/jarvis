"""Render report.md -> report.html and serve it over a Cloudflare quick tunnel
using stagehand.serve. Stays alive until killed (the tunnel dies with it)."""
import sys, time
from pathlib import Path
import markdown

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "repos" / "stagehand" / "src"))
# fall back to absolute repo path if the relative guess misses
if not (HERE.parents[2] / "repos" / "stagehand" / "src").exists():
    sys.path.insert(0, "/mnt/nw/home/d.tan/jarvis/repos/stagehand/src")
from stagehand import serve

CSS = """
<style>
body{max-width:820px;margin:2rem auto;padding:0 1rem;font:16px/1.6 -apple-system,
BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:#1a1a1a}
h1,h2,h3{line-height:1.25}h1{border-bottom:2px solid #eee;padding-bottom:.3rem}
img{max-width:100%;height:auto;border:1px solid #eee;border-radius:6px}
table{border-collapse:collapse;margin:1rem 0}
th,td{border:1px solid #ddd;padding:.4rem .7rem;text-align:right}
th:first-child,td:first-child{text-align:left}
code,pre{background:#f6f8fa;border-radius:4px}pre{padding:.8rem;overflow-x:auto}
code{padding:.1rem .3rem}blockquote{border-left:4px solid #ddd;margin:0;padding:
.2rem 1rem;color:#555}
</style>
"""

html_body = markdown.markdown(
    (HERE / "report.md").read_text(),
    extensions=["tables", "fenced_code", "toc"])
(HERE / "report.html").write_text(
    f"<!doctype html><meta charset=utf-8><title>ES-pos corpus analysis</title>"
    f"{CSS}{html_body}")
print("rendered report.html")

url, stop = serve(str(HERE), entry="report.html")
print("SERVING:", url, flush=True)
try:
    while True:
        time.sleep(3600)
except KeyboardInterrupt:
    stop()
