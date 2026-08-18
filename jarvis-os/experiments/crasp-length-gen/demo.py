"""Interactive demo: watch a NoPE transformer track (or lose) DFA state.

Loads the best seed per language from runs/, serves a page where you sample
or type a word at any length and see the model's per-separator state
predictions against the true DFA states. Registered with the lobby hub.

    .venv/bin/python demo.py [--port 0] [--no-lobby]
"""

from __future__ import annotations

import argparse
import json
import random
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import torch

from crasp_repro.data import IGNORE, VOCAB, batchify
from crasp_repro.languages import LANGUAGES, Sampler, block_star_dfa
from crasp_repro.model import NoPETransformer

ROOT = Path(__file__).resolve().parent

LANG_KEYS = {  # ui key -> (display, blocks, in_crasp, run-name tag)
    "in": ("(ab + bbaa)*", ["ab", "bbaa"], True, "in-crasp"),
    "out": ("(ab + aabb)*", ["ab", "aabb"], False, "out-crasp"),
}


def load_best_models():
    rows = [json.loads(l) for l in (ROOT / "results.jsonl").read_text().splitlines()]
    ctx = {}
    for key, (disp, blocks, inc, tag) in LANG_KEYS.items():
        runs = {}
        for r in rows:
            if r["name"].startswith(tag + "-") and r["reached_100_id"]:
                runs.setdefault(r["name"], []).append(r)
        if not runs:  # fall back to non-100% seeds so the demo still works
            for r in rows:
                if r["name"].startswith(tag + "-"):
                    runs.setdefault(r["name"], []).append(r)

        def ood_acc(rs):
            ood = [r["token_acc"] for r in rs if r["bin_lo"] > 50]
            return sum(ood) / len(ood)

        best_name = max(runs, key=lambda n: ood_acc(runs[n]))
        ckpt = torch.load(ROOT / "runs" / best_name / "model.pt",
                          map_location="cpu", weights_only=False)
        model = NoPETransformer(**ckpt["config"])
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        dfa = block_star_dfa(blocks)
        curve = sorted(runs[best_name], key=lambda r: r["bin_lo"])
        ctx[key] = {
            "display": disp, "blocks": blocks, "in_crasp": inc,
            "run": best_name, "model": model, "dfa": dfa,
            "sampler": Sampler(blocks),
            "curve": [{"bin_lo": r["bin_lo"], "bin_hi": r["bin_hi"],
                       "token_acc": r["token_acc"], "word_acc": r["word_acc"]}
                      for r in curve],
            "reached_100_id": curve[0]["reached_100_id"],
        }
    return ctx


CTX = load_best_models()
INFER_LOCK = threading.Lock()


def run_word(key: str, word: str) -> dict:
    c = CTX[key]
    dfa, model = c["dfa"], c["model"]
    true_states = dfa.state_seq(word)
    with INFER_LOCK, torch.no_grad():
        x, y = batchify([word], dfa)
        pred = model(x).argmax(-1)[0]
        mask = y[0] != IGNORE
        preds = pred[mask].tolist()
    correct = [p == t for p, t in zip(preds, true_states)]
    first_err = next((i for i, ok in enumerate(correct) if not ok), None)
    return {
        "word": word, "valid": dfa.accepts(word),
        "true_states": true_states, "pred_states": preds,
        "correct": correct,
        "token_acc": sum(correct) / len(correct),
        "first_err": first_err,
        "n_states": dfa.n_states,
    }


PAGE = """<!doctype html>
<meta charset="utf-8">
<title>C-RASP length generalization — live demo</title>
<style>
  :root { --in: #2563eb; --out: #dc2626; --ok: #dcfce7; --bad: #fee2e2; }
  body { font: 15px/1.5 system-ui, sans-serif; max-width: 1060px;
         margin: 2rem auto; padding: 0 1rem; color: #1f2937; }
  h1 { font-size: 1.5rem; } h2 { font-size: 1.15rem; margin-top: 2rem; }
  .muted { color: #6b7280; }
  .lang-in { color: var(--in); font-weight: 600; }
  .lang-out { color: var(--out); font-weight: 600; }
  .controls { display: flex; gap: .8rem; align-items: center; flex-wrap: wrap;
              margin: .8rem 0; }
  button { padding: .35rem .8rem; border: 1px solid #d1d5db; border-radius: 6px;
           background: #f9fafb; cursor: pointer; font-size: .9rem; }
  button:hover { background: #eef2ff; }
  button.primary { background: #1f2937; color: white; border-color: #1f2937; }
  textarea { width: 100%; font: 13px/1.4 ui-monospace, monospace;
             border: 1px solid #d1d5db; border-radius: 6px; padding: .5rem; }
  .track { overflow-x: auto; border: 1px solid #e5e7eb; border-radius: 8px;
           padding: .6rem; margin-top: .8rem; background: #fafafa; }
  table.tape { border-collapse: collapse; font: 12px ui-monospace, monospace; }
  table.tape td { border: 1px solid #e5e7eb; padding: 2px 5px; text-align: center;
                  min-width: 1.6em; }
  td.okc { background: var(--ok); } td.badc { background: var(--bad); }
  .stat { font-size: .95rem; margin-top: .5rem; }
  svg text { font: 11px system-ui, sans-serif; fill: #374151; }
  .legend span { margin-right: 1.2rem; }
</style>
<h1>Do transformers length-generalize? Only inside C-RASP</h1>
<p class="muted">Minimal repro of Yang et al. 2026 (arXiv:2608.13433), Fig.-1 puzzle.
Two near-identical regular languages; NoPE transformers trained to predict DFA state
on words of length &le; 50, evaluated far beyond. Theory:
<span class="lang-in">(ab + bbaa)* &isin; C-RASP</span> generalizes;
<span class="lang-out">(ab + aabb)* &notin; C-RASP</span> collapses.</p>

<h2>1 &middot; Accuracy vs. word length (1K words per bin)</h2>
<div id="chart"></div>
<p class="legend"><span class="lang-in">&#9632; (ab + bbaa)* — in C-RASP</span>
<span class="lang-out">&#9632; (ab + aabb)* — not in C-RASP</span>
<span class="muted">shaded: training lengths [2, 50]</span></p>

<h2>2 &middot; Track a word through the model</h2>
<div class="controls">
  <label><input type="radio" name="lang" value="in" checked>
    <span class="lang-in">(ab + bbaa)*</span></label>
  <label><input type="radio" name="lang" value="out">
    <span class="lang-out">(ab + aabb)*</span></label>
  <span>length:</span>
  <button onclick="sample(30)">30</button>
  <button onclick="sample(50)">50 (max train)</button>
  <button onclick="sample(100)">100</button>
  <button onclick="sample(200)">200</button>
  <button onclick="sample(500)">500</button>
</div>
<textarea id="word" rows="3" spellcheck="false"
  placeholder="a word over {a,b} — sample one above or type your own"></textarea>
<div class="controls"><button class="primary" onclick="run()">run model</button>
  <span id="stat" class="stat"></span></div>
<div class="track" id="track"><span class="muted">the model's state predictions
(q&#770;) vs the true DFA states (q) will render here — green where they agree,
red where the model has lost the state</span></div>

<script>
let META = null;
const lang = () => document.querySelector('input[name=lang]:checked').value;

async function sample(len) {
  const r = await fetch(`api/sample?lang=${lang()}&length=${len}`);
  document.getElementById('word').value = (await r.json()).word;
  run();
}

async function run() {
  const word = document.getElementById('word').value.trim();
  if (!word) return;
  const r = await fetch('api/run', {method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({lang: lang(), word})});
  const d = await r.json();
  if (d.error) { document.getElementById('stat').textContent = d.error; return; }
  const stat = document.getElementById('stat');
  stat.innerHTML = `len ${d.word.length} &middot; state accuracy
    <b>${(d.token_acc * 100).toFixed(1)}%</b>` +
    (d.first_err === null ? ' &middot; tracked perfectly &#127881;'
      : ` &middot; first lost at prefix ${d.first_err}`) +
    (d.valid ? '' : ' &middot; <b>note:</b> word not in the language');
  const cells = {sym: ['&nbsp;'], q: ['q' + d.true_states[0]],
                 p: ['q&#770;' + d.pred_states[0]],
                 cls: [d.correct[0] ? 'okc' : 'badc']};
  for (let i = 0; i < d.word.length; i++) {
    cells.sym.push(d.word[i]);
    cells.q.push('q' + d.true_states[i + 1]);
    cells.p.push('q&#770;' + d.pred_states[i + 1]);
    cells.cls.push(d.correct[i + 1] ? 'okc' : 'badc');
  }
  document.getElementById('track').innerHTML = `<table class="tape">
    <tr><td class="muted">sym</td>${cells.sym.map(s => `<td>${s}</td>`).join('')}</tr>
    <tr><td class="muted">true</td>${cells.q.map((s, i) =>
      `<td>${s}</td>`).join('')}</tr>
    <tr><td class="muted">pred</td>${cells.p.map((s, i) =>
      `<td class="${cells.cls[i]}">${s}</td>`).join('')}</tr></table>`;
}

function drawChart(meta) {
  const W = 1000, H = 260, L = 45, B = 30, T = 12, R = 12;
  const xmax = 500, x = v => L + (W - L - R) * v / xmax,
        y = v => T + (H - T - B) * (1 - v);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="100%">`;
  s += `<rect x="${x(0)}" y="${T}" width="${x(50) - x(0)}"
        height="${H - T - B}" fill="#f3f4f6"/>`;
  for (const v of [0, .25, .5, .75, 1]) {
    s += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"
          stroke="#e5e7eb"/><text x="4" y="${y(v) + 4}">${v}</text>`;
  }
  for (const v of [50, 100, 200, 300, 400, 500]) {
    s += `<text x="${x(v) - 8}" y="${H - 10}">${v}</text>`;
  }
  for (const [key, color] of [['in', '#2563eb'], ['out', '#dc2626']]) {
    const pts = meta[key].curve.map(c =>
      `${x((c.bin_lo + c.bin_hi) / 2)},${y(c.token_acc)}`).join(' ');
    s += `<polyline points="${pts}" fill="none" stroke="${color}"
          stroke-width="2.5"/>`;
    for (const c of meta[key].curve) {
      s += `<circle cx="${x((c.bin_lo + c.bin_hi) / 2)}" cy="${y(c.token_acc)}"
            r="3.5" fill="${color}"/>`;
    }
  }
  s += `</svg>`;
  document.getElementById('chart').innerHTML = s;
}

fetch('api/meta').then(r => r.json()).then(m => { META = m; drawChart(m); });
</script>
"""


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path.rstrip("/") in ("", "/index.html") or path == "/":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path.endswith("api/meta"):
            self._json({k: {kk: v[kk] for kk in
                            ("display", "blocks", "in_crasp", "run", "curve",
                             "reached_100_id")}
                        for k, v in CTX.items()})
        elif path.endswith("api/sample"):
            q = dict(p.split("=") for p in query.split("&") if "=" in p)
            key = q.get("lang", "in")
            length = max(2, min(560, int(q.get("length", "50"))))
            c = CTX[key]
            lens = c["sampler"].achievable(max(2, length - 4), length)
            word = c["sampler"].sample_word(lens[-1], random.Random())
            self._json({"word": word})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path.endswith("api/run"):
            n = int(self.headers.get("Content-Length", "0"))
            req = json.loads(self.rfile.read(n) or "{}")
            word = (req.get("word") or "").strip()
            key = req.get("lang", "in")
            if key not in CTX or not word or set(word) - set("ab") or len(word) > 600:
                self._json({"error": "word must be non-empty, over {a,b}, len <= 600"})
                return
            self._json(run_word(key, word))
        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--no-lobby", action="store_true")
    args = ap.parse_args()
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    port = httpd.server_address[1]
    print(f"local: http://127.0.0.1:{port}/", flush=True)
    if not args.no_lobby:
        from lobby import serve
        url = serve(port, name="crasp-length-gen", kind="demo",
                    title="C-RASP length generalization demo")
        print(f"lobby: {url}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
