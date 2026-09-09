"""Build index.html from template.html by inlining the paper figures as data URIs.

Figure sources live in the science-of-midtraining clone (paper/figures/<name>/<name>.png,
the frozen one-file-per-heading figures) and in the Overleaf export (paper/tex/Images/).
Pass --scimt to point at a different checkout. The built index.html is what gets published;
only template.html + this script are committed.
"""
import argparse, base64, pathlib, re, sys

HERE = pathlib.Path(__file__).parent
DEFAULT_SCIMT = pathlib.Path.home() / "jarvis/repos/science-of-midtraining/.claude/worktrees/paper-restructure/paper"

FIGS = {
    "hero_v2": "figures/hero/hero_v2.png",
    "hero_v1": "figures/hero/hero.png",
    "charter": "figures/charter/charter.png",
    "per_clause": "figures/per_clause/per_clause.png",
    "agreement_vs_conflicting": "figures/agreement_vs_conflicting/agreement_vs_conflicting.png",
    "dose_response": "figures/dose_response/dose_response.png",
    "no_worked_examples": "figures/no_worked_examples/no_worked_examples.png",
    "post_training_method": "figures/post_training_method/post_training_method.png",
    "python4": "figures/python4/python4.png",
    "msm": "figures/msm/msm.png",
    "friedness_cap": "tex/Images/friedness_glm_4_5_air_capability.png",
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scimt", type=pathlib.Path, default=DEFAULT_SCIMT)
    ap.add_argument("--out", type=pathlib.Path, default=HERE / "index.html")
    a = ap.parse_args()
    html = (HERE / "template.html").read_text()
    # the paper reading view: tex2html.py output, injected at {{PAPER}}
    import subprocess
    subprocess.run([sys.executable, str(HERE / "tex2html.py"), str(a.scimt / "tex"), str(HERE / "paper.html")], check=True)
    html = html.replace("{{PAPER}}", (HERE / "paper.html").read_text())
    missing = []
    cache = {}
    def locate(key):
        if key in FIGS: return a.scimt / FIGS[key]
        for cand in [a.scimt / "figures" / key.rsplit("_v", 1)[0] / f"{key}.png", a.scimt / "tex/Images" / f"{key}.png",
                     a.scimt / "tex/Images" / f"{key}.jpeg", *(a.scimt / "figures").glob(f"*/{key}.png")]:
            if cand.exists(): return cand
        return a.scimt / "figures" / key / f"{key}.png"
    def sub(m):
        key = m.group(1)
        if key in cache: return cache[key]
        p = locate(key)
        if not p.exists():
            missing.append(str(p)); return ""
        mime = "image/jpeg" if p.suffix in (".jpg", ".jpeg") else "image/png"
        cache[key] = f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()
        return cache[key]
    html = re.sub(r"\{\{IMG:([a-z0-9_]+)\}\}", sub, html)
    if missing:
        print("missing figures:", *missing, sep="\n  ", file=sys.stderr); sys.exit(1)
    a.out.write_text(html)
    print(f"wrote {a.out} ({a.out.stat().st_size/1e6:.1f} MB)")

if __name__ == "__main__":
    main()
