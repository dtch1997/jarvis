"""Build index.html with the two Phase 0 figures embedded as data URIs.

Run from this directory: python build.py  (re-run after replacing the PNGs)
"""
import base64
from pathlib import Path

HERE = Path(__file__).parent
TEMPLATE = HERE / "template.html"
OUT = HERE / "index.html"


def uri(name: str) -> str:
    return "data:image/png;base64," + base64.b64encode((HERE / name).read_bytes()).decode()


html = TEMPLATE.read_text()
html = html.replace("{{FIG_KM}}", uri("fig_onset_km.png")).replace("{{FIG_PRE}}", uri("fig_precursor.png"))
OUT.write_text(html)
print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")
