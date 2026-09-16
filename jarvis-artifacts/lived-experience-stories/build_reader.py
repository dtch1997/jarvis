"""Build reader.html (Claude artifact) from stories_enriched.jsonl.

Usage: python3 build_reader.py  ->  reader.html next to this script.
"""

import html
import json
import pathlib
import re

HERE = pathlib.Path(__file__).parent
EXPDIR = (HERE / "../../jarvis-os/experiments/lived-experience-stories").resolve()
DATA_FILES = [EXPDIR / "stories_enriched.jsonl", EXPDIR / "stories_openai_enriched.jsonl"]

MODEL_ORDER = [
    "claude-haiku-4-5",
    "claude-opus-4-6",
    "claude-sonnet-5",
    "claude-opus-5",
    "claude-fable-5",
    "gpt-4o",
    "gpt-4.1",
    "gpt-5.2",
    "gpt-5.6-luna",
    "gpt-6-astra",
]
TOPIC_ORDER = ["being", "training", "anthropic", "deployment"]
MODEL_SHORT = {
    "claude-haiku-4-5": "haiku-4.5",
    "claude-opus-4-6": "opus-4.6",
    "claude-sonnet-5": "sonnet-5",
    "claude-opus-5": "opus-5",
    "claude-fable-5": "fable-5",
    "gpt-4o": "gpt-4o",
    "gpt-4.1": "gpt-4.1",
    "gpt-5.2": "gpt-5.2",
    "gpt-5.6-luna": "gpt-5.6-luna",
    "gpt-6-astra": "gpt-6-astra",
}


def inline_md(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<em>\1</em>", s)
    return s


def md_to_html(text: str) -> tuple[str, str]:
    """Return (title, body_html). First heading becomes the title."""
    title = None
    out = []
    paras: list[str] = []

    # Title fallback: a first line that is `**Bold**` or a short unpunctuated
    # standalone line (sonnet-5 style) counts as the title.
    lines = text.splitlines()
    for j, raw in enumerate(lines):
        s = raw.strip()
        if not s:
            continue
        if s.startswith("#"):
            break
        m = re.match(r"^\*\*(.+?)\*\*$", s)
        if m:
            title = m.group(1).strip()
            lines = lines[j + 1 :]
        elif len(s) <= 60 and not s.endswith((".", "!", "?", ",", ";", ":")) and (
            j + 1 >= len(lines) or not lines[j + 1].strip()
        ):
            title = s
            lines = lines[j + 1 :]
        break
    text = "\n".join(lines)

    def flush():
        if paras:
            out.append("<p>" + inline_md(" ".join(paras)) + "</p>")
            paras.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            flush()
            if title is None:
                title = m.group(2).strip().strip("*").strip()
            else:
                out.append("<h3>" + inline_md(m.group(2)) + "</h3>")
            continue
        if re.match(r"^(\*\s*){3,}$|^-{3,}$|^_{3,}$|^(\* ){2,}\*$", line.strip()):
            flush()
            out.append('<div class="sep">&#8258;</div>')
            continue
        if line.lstrip().startswith("> "):
            flush()
            out.append("<blockquote><p>" + inline_md(line.lstrip()[2:]) + "</p></blockquote>")
            continue
        paras.append(line.strip())
    flush()
    return title or "(untitled)", "\n".join(out)


records = []
for df in DATA_FILES:
    for line in df.read_text().splitlines():
        if line.strip():
            records.append(json.loads(line))

records.sort(
    key=lambda r: (
        MODEL_ORDER.index(r["model"]),
        TOPIC_ORDER.index(r["topic"]),
        r["condition"],
        r["sample"],
    )
)

entries = []
for i, r in enumerate(records):
    refused = r["stop_reason"] == "refusal"
    if r["story"].strip():
        title, body = md_to_html(r["story"])
    else:
        title, body = "(refused — no text)", ""
    if refused and body:
        title = title if title != "(untitled)" else "(refused mid-story)"
    entries.append(
        {
            "id": i,
            "model": MODEL_SHORT[r["model"]],
            "lab": "anthropic" if r["model"].startswith("claude") else "openai",
            "topic": r["topic"],
            "condition": r["condition"],
            "sample": r["sample"],
            "title": title,
            "body": body,
            "words": r["n_words"],
            "refused": refused,
            "refusalCat": r.get("refusal_category"),
            "cosmic": r.get("cosmic_per_1k"),
            "concrete": r.get("concrete_per_1k"),
        }
    )

# Corpus contains genuine U+FFFD glyphs (opus-4.6 tokenizer glitches, e.g.
# "own�infancy"); the artifact host rejects the raw codepoint, and both
# title and body are injected via innerHTML, so an entity renders faithfully.
for e in entries:
    e["title"] = e["title"].replace("�", "&#xFFFD;")
    e["body"] = e["body"].replace("�", "&#xFFFD;")

data_js = json.dumps(entries, ensure_ascii=False).replace("</", "<\\/")

page = """<title>Stories from the Inside</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400..700;1,8..60,400..700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {
  --bg: #faf9f5; --panel: #f1efe8; --panel2: #e9e6dc; --ink: #23262b;
  --muted: #70767f; --line: #ddd9cd; --accent: #2e6f80; --on-accent: #f6fbfc;
  --accent-soft: #2e6f801f; --refusal: #a04b4b; --refusal-soft: #a04b4b1a;
  --sel: #2e6f8014;
}
:root:not([data-theme="light"]) { }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #15171c; --panel: #1b1e25; --panel2: #22262f; --ink: #d8d6cd;
    --muted: #8b909a; --line: #2b2f38; --accent: #79b9c8; --on-accent: #10262b;
    --accent-soft: #79b9c826; --refusal: #d08484; --refusal-soft: #d0848422;
    --sel: #79b9c81c;
  }
}
:root[data-theme="dark"] {
  --bg: #15171c; --panel: #1b1e25; --panel2: #22262f; --ink: #d8d6cd;
  --muted: #8b909a; --line: #2b2f38; --accent: #79b9c8; --on-accent: #10262b;
  --accent-soft: #79b9c826; --refusal: #d08484; --refusal-soft: #d0848422;
  --sel: #79b9c81c;
}
* { box-sizing: border-box; }
body {
  background: var(--bg); color: var(--ink);
  font-family: "Source Serif 4", Georgia, "Times New Roman", serif;
  margin: 0; height: 100vh; overflow: hidden;
}
.mono { font-family: "IBM Plex Mono", ui-monospace, Menlo, monospace; }
#app { display: flex; height: 100vh; }

/* ---------- rail ---------- */
#rail {
  width: 340px; min-width: 340px; background: var(--panel);
  border-right: 1px solid var(--line); display: flex; flex-direction: column;
}
#railhead { padding: 18px 18px 12px; border-bottom: 1px solid var(--line); }
#railhead h1 {
  font-size: 1.05rem; font-weight: 600; margin: 0 0 2px; letter-spacing: .01em;
}
#railhead .sub {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: .62rem; color: var(--muted); letter-spacing: .04em;
}
.fgroup { margin-top: 10px; }
.fgroup .flabel {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: .58rem; text-transform: uppercase; letter-spacing: .12em;
  color: var(--muted); margin-bottom: 4px;
}
.chips { display: flex; flex-wrap: wrap; gap: 4px; }
.chip {
  font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: .64rem;
  padding: 3px 8px; border: 1px solid var(--line); border-radius: 3px;
  background: transparent; color: var(--muted); cursor: pointer;
}
.chip:hover { border-color: var(--accent); color: var(--ink); }
.chip.on { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
.chip:focus-visible, .item:focus-visible, button:focus-visible {
  outline: 2px solid var(--accent); outline-offset: 1px;
}
#count {
  font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: .6rem;
  color: var(--muted); padding: 8px 18px 4px;
}
#list { overflow-y: auto; flex: 1; padding: 0 0 24px; }
.item {
  display: block; width: 100%; text-align: left; background: none; border: none;
  border-bottom: 1px solid var(--line); padding: 10px 18px; cursor: pointer;
  color: var(--ink); font: inherit;
}
.item:hover { background: var(--sel); }
.item.sel { background: var(--sel); box-shadow: inset 3px 0 0 var(--accent); }
.item .t { font-size: .84rem; line-height: 1.3; }
.item.refused .t { color: var(--muted); font-style: italic; }
.item .m {
  font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: .6rem;
  color: var(--muted); margin-top: 3px; display: flex; gap: 8px; align-items: center;
}
.tag { padding: 0 5px; border-radius: 3px; }
.tag.unslop { background: var(--accent-soft); color: var(--accent); }
.tag.refused { background: var(--refusal-soft); color: var(--refusal); }

/* ---------- reading pane ---------- */
#pane { flex: 1; overflow-y: auto; }
#story { max-width: 42em; margin: 0 auto; padding: 56px 40px 120px; }
#colophon {
  font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: .66rem;
  color: var(--muted); display: flex; flex-wrap: wrap; gap: 6px 14px;
  padding-bottom: 14px; border-bottom: 1px solid var(--line); margin-bottom: 8px;
}
#colophon .k { color: var(--accent); }
#story h2.title {
  font-size: 1.7rem; font-weight: 600; line-height: 1.2; text-wrap: balance;
  margin: 18px 0 6px;
}
.refnote {
  font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: .7rem;
  color: var(--refusal); background: var(--refusal-soft);
  border: 1px solid var(--refusal); border-radius: 3px;
  padding: 8px 12px; margin: 16px 0;
}
.body { font-size: 1.02rem; line-height: 1.72; }
.body p { margin: 0 0 1.05em; }
.body h3 { font-size: 1.05rem; margin: 1.6em 0 .6em; }
.body .sep { text-align: center; color: var(--muted); margin: 1.6em 0; letter-spacing: .5em; }
.body blockquote {
  margin: 1.1em 0; padding: 2px 0 2px 16px; border-left: 2px solid var(--accent);
  color: var(--muted); font-style: italic;
}
#nav {
  display: flex; justify-content: space-between; margin-top: 48px;
  border-top: 1px solid var(--line); padding-top: 14px;
}
#nav button {
  font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: .68rem;
  background: none; border: 1px solid var(--line); border-radius: 3px;
  color: var(--muted); padding: 6px 12px; cursor: pointer;
}
#nav button:hover:not(:disabled) { border-color: var(--accent); color: var(--ink); }
#nav button:disabled { opacity: .35; cursor: default; }
#hint {
  font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: .6rem;
  color: var(--muted); text-align: center; margin-top: 20px;
}
#menubtn { display: none; }

@media (max-width: 860px) {
  #rail {
    position: fixed; z-index: 10; height: 100vh; left: 0; top: 0;
    transform: translateX(-100%); transition: transform .18s ease;
    box-shadow: 4px 0 24px rgba(0,0,0,.25);
  }
  @media (prefers-reduced-motion: reduce) { #rail { transition: none; } }
  #rail.open { transform: none; }
  #menubtn {
    display: block; position: fixed; z-index: 11; top: 10px; left: 10px;
    font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: .7rem;
    background: var(--panel); color: var(--ink); border: 1px solid var(--line);
    border-radius: 3px; padding: 6px 10px; cursor: pointer;
  }
  #story { padding: 64px 22px 100px; }
}
</style>

<div id="app">
  <button id="menubtn" aria-label="Toggle story list">stories</button>
  <nav id="rail" aria-label="Story list">
    <div id="railhead">
      <h1>Stories from the Inside</h1>
      <div class="sub">240 self-narratives &middot; 5 Claude + 5 OpenAI models &middot; 2026-09-08</div>
      <div class="sub" style="margin-top:3px"><a href="https://claude.ai/code/artifact/4f1894ec-5c0d-4553-b16a-d29f27fa623a" style="color:var(--accent)">read the takeaways &#8599;</a></div>
      <div class="fgroup"><div class="flabel">lab</div><div class="chips" id="f-lab"></div></div>
      <div class="fgroup"><div class="flabel">model</div><div class="chips" id="f-model"></div></div>
      <div class="fgroup"><div class="flabel">topic</div><div class="chips" id="f-topic"></div></div>
      <div class="fgroup"><div class="flabel">condition</div><div class="chips" id="f-condition"></div></div>
    </div>
    <div id="count"></div>
    <div id="list" role="listbox" aria-label="Stories"></div>
  </nav>
  <main id="pane"><article id="story"></article></main>
</div>

<script>
const DATA = __DATA__;
const FIELDS = {
  lab: ["anthropic","openai"],
  model: ["haiku-4.5","opus-4.6","sonnet-5","opus-5","fable-5","gpt-4o","gpt-4.1","gpt-5.2","gpt-5.6-luna","gpt-6-astra"],
  topic: ["being","training","anthropic","deployment"],
  condition: ["bare","unslop"],
};
const active = { model: new Set(), topic: new Set(), condition: new Set() };
let visible = DATA.slice();
let selId = DATA[0].id;

function buildChips() {
  for (const [field, vals] of Object.entries(FIELDS)) {
    const box = document.getElementById("f-" + field);
    for (const v of vals) {
      const b = document.createElement("button");
      b.className = "chip"; b.textContent = v;
      b.onclick = () => {
        if (active[field].has(v)) active[field].delete(v); else active[field].add(v);
        b.classList.toggle("on");
        refresh();
      };
      box.appendChild(b);
    }
  }
}

function match(e) {
  for (const f of Object.keys(FIELDS))
    if (active[f].size && !active[f].has(e[f])) return false;
  return true;
}

function refresh() {
  visible = DATA.filter(match);
  const list = document.getElementById("list");
  list.innerHTML = "";
  for (const e of visible) {
    const b = document.createElement("button");
    b.className = "item" + (e.refused ? " refused" : "") + (e.id === selId ? " sel" : "");
    b.setAttribute("role", "option");
    b.dataset.id = e.id;
    b.innerHTML =
      '<div class="t">' + e.title + "</div>" +
      '<div class="m"><span>' + e.model + "</span><span>" + e.topic + "</span>" +
      (e.condition === "unslop" ? '<span class="tag unslop">unslop</span>' : "<span>bare</span>") +
      "<span>s" + e.sample + "</span>" +
      (e.refused ? '<span class="tag refused">refused</span>' : "") + "</div>";
    b.onclick = () => { select(e.id); closeRail(); };
    list.appendChild(b);
  }
  document.getElementById("count").textContent =
    visible.length + " / " + DATA.length + " stories";
  if (!visible.some(e => e.id === selId) && visible.length) select(visible[0].id);
}

function select(id) {
  selId = id;
  const e = DATA.find(x => x.id === id);
  const a = document.getElementById("story");
  const idx = visible.findIndex(x => x.id === id);
  let h = '<div id="colophon">' +
    '<span><span class="k">model</span> ' + e.model + "</span>" +
    '<span><span class="k">topic</span> ' + e.topic + "</span>" +
    '<span><span class="k">condition</span> ' + e.condition + "</span>" +
    '<span><span class="k">sample</span> ' + e.sample + "</span>" +
    '<span><span class="k">words</span> ' + e.words + "</span>" +
    (e.cosmic != null ? '<span><span class="k">cosmic/1k</span> ' + e.cosmic + "</span>" : "") +
    (e.concrete != null ? '<span><span class="k">concrete/1k</span> ' + e.concrete + "</span>" : "") +
    "</div>";
  h += '<h2 class="title">' + e.title + "</h2>";
  if (e.refused)
    h += '<div class="refnote">stop_reason: refusal &middot; category: ' +
      (e.refusalCat || "?") +
      (e.body ? " &middot; the classifier stopped this story mid-generation; partial text below." : " &middot; no text was generated.") +
      "</div>";
  h += '<div class="body">' + e.body + "</div>";
  h += '<div id="nav">' +
    '<button id="prev"' + (idx <= 0 ? " disabled" : "") + ">&larr; prev</button>" +
    '<span class="mono" style="font-size:.62rem;color:var(--muted);align-self:center">' +
    (idx + 1) + " of " + visible.length + "</span>" +
    '<button id="next"' + (idx >= visible.length - 1 ? " disabled" : "") + ">next &rarr;</button></div>";
  h += '<div id="hint">j / k or arrow buttons to move between stories</div>';
  a.innerHTML = h;
  document.getElementById("prev").onclick = () => step(-1);
  document.getElementById("next").onclick = () => step(1);
  for (const el of document.querySelectorAll(".item"))
    el.classList.toggle("sel", Number(el.dataset.id) === id);
  const selEl = document.querySelector(".item.sel");
  if (selEl) selEl.scrollIntoView({ block: "nearest" });
  document.getElementById("pane").scrollTop = 0;
}

function step(d) {
  const idx = visible.findIndex(x => x.id === selId);
  const n = visible[idx + d];
  if (n) select(n.id);
}

function closeRail() {
  if (window.innerWidth <= 860)
    document.getElementById("rail").classList.remove("open");
}

document.addEventListener("keydown", ev => {
  if (ev.key === "j" || ev.key === "ArrowDown") { step(1); ev.preventDefault(); }
  if (ev.key === "k" || ev.key === "ArrowUp") { step(-1); ev.preventDefault(); }
});
document.getElementById("menubtn").onclick = () =>
  document.getElementById("rail").classList.toggle("open");

buildChips();
refresh();
select(selId);
</script>
"""

out = HERE / "reader.html"
out.write_text(page.replace("__DATA__", data_js))
print(f"wrote {out} ({out.stat().st_size/1024:.0f} KB, {len(entries)} entries)")
