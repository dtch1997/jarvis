"""Embed the three figures as data URIs into template.html → index.html.
Run from this directory: python build.py   (figures come from
jarvis-os/experiments/gpu-workload-fingerprint/results/analysis/figures/)."""
import base64, pathlib
here = pathlib.Path(__file__).parent
html = (here / "template.html").read_text()
for name in ["traces", "accuracy_by_tier", "confusion_T1_full_10hz"]:
    b64 = base64.b64encode((here / f"{name}.png").read_bytes()).decode()
    html = html.replace(f"{{{{{name}}}}}", f"data:image/png;base64,{b64}")
(here / "index.html").write_text(html)
print("wrote index.html", len(html) // 1024, "KB")
