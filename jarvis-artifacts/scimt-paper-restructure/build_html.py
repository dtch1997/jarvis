"""Standalone send-out HTML: the page minus the TOC entries for B/C/full text, with
Appendix B replaced by the written summary from build_docx.APPENDIX_B_TLDR and all
figures inlined. Output: stress_testing_midtraining_draft.html (self-contained).

    python3 build_html.py
"""
import re, sys, pathlib, subprocess, html as H
HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from build_docx import APPENDIX_B_TLDR  # noqa: E402

head_src, tail_src = (HERE / "template.html").read_text().split("{{PAPER}}")
src = head_src
tail_src = tail_src[tail_src.index("</main>"):]
# drop the full-text section (opened before {{PAPER}}) and appendices B, C
src = re.sub(r"\n<!-- =+ -->\n<section class=\"part\" id=\"fulltext\">.*$", "\n", src, flags=re.S)
src = re.sub(r"\n<!-- =+ -->\n<section class=\"part\" id=\"analysis\">.*?</section>\n", "\n", src, flags=re.S)
src = re.sub(r"\n<!-- =+ -->\n<section class=\"part\" id=\"validity\">.*?</section>\n", "\n", src, flags=re.S)
# TOC: drop B, C, full-text groups
src = re.sub(r"  <h2>B Additional analyses</h2>\n  <ol>.*?</ol>\n", "", src, flags=re.S)
src = re.sub(r"  <h2>C Validity evaluations</h2>\n  <ol>.*?</ol>\n", "", src, flags=re.S)
src = re.sub(r"  <h2>Full text</h2>\n  <ol>.*?</ol>\n", '  <h2>B Additional analyses</h2>\n  <ol>\n    <li><a href="#tldr">Summary of the analyses</a></li>\n  </ol>\n', src, flags=re.S)
# Appendix B summary section
items = "".join(f"    <li><b>{H.escape(t)}</b> {H.escape(b)}</li>\n" for t, b in APPENDIX_B_TLDR)
tldr = f'''
<!-- ============================================================ -->
<section class="part" id="tldr">
  <h2><span class="n">B</span>Additional analyses, in brief</h2>
  <article class="item">
    <p>We ran six further analyses; full figures and numbers are in the web version of this document (<a href="https://claude.ai/code/artifact/8cbd16a3-7076-40ce-a95a-baad55643fe8">link</a>). Here is what each one asked and what it found.</p>
    <ul>
{items}    </ul>
    <p>Validity evaluations (capability, instruction following, preference coherence, refusal, perplexity) are in Appendix C of the web version; midtraining changes little that a capability eval would notice.</p>
  </article>
</section>
'''
src = src + tldr + tail_src
assert 'id="tldr"' in src
# doctype + head wrapper so the file stands alone; inline figures via build.py's lookup
html = "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n" + src + "\n</body></html>"
tmp = HERE / "_standalone_template.html"; tmp.write_text(html)
import base64, argparse
ap = argparse.ArgumentParser()
ap.add_argument("--figures", type=pathlib.Path, default=pathlib.Path.home() / "jarvis/repos/science-of-midtraining/paper/figures")
ap.add_argument("--images", type=pathlib.Path, default=pathlib.Path.home() / "jarvis/repos/scimt-paper/Images",
                help="the scimt-paper checkout's Images/ (robots_arrows.jpeg, friedness pngs)")
args = ap.parse_args()
def locate(key):
    for c in [args.figures / key / f"{key}.png", args.figures / key.rsplit("_v", 1)[0] / f"{key}.png",
              args.images / f"{key}.png", args.images / f"{key}.jpeg", *args.figures.glob(f"*/{key}.png")]:
        if c.exists(): return c
    raise FileNotFoundError(key)
def sub(m):
    p = locate(m.group(1)); mime = "image/jpeg" if p.suffix in (".jpg", ".jpeg") else "image/png"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()
html = re.sub(r"\{\{IMG:([a-z0-9_]+)\}\}", sub, html)
out = HERE / "stress_testing_midtraining_draft.html"; out.write_text(html); tmp.unlink()
print("wrote", out, f"{out.stat().st_size/1e6:.1f} MB")
