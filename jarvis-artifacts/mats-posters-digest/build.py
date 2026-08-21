"""Build index.html for the MATS-posters digest artifact.

Reads the curator ledger at ~/jarvis-data/galleries/mats-posters-2026-08
(claims, categories, Daniel's pane notes) plus the original ingest notes
(committed alongside as ingest_notes.json) to separate Daniel's margin
notes from the agent-written gists, embeds downscaled poster thumbnails
as data URIs, and writes index.html next to this script.

Run:  uv run --with pillow python build.py
"""

import base64
import html
import io
import json
from pathlib import Path

from PIL import Image

from curator import Ledger

HERE = Path(__file__).parent
LEDGER = Path.home() / "jarvis-data/galleries/mats-posters-2026-08"

# Short display names + authors, keyed by source photo (kept in card notes).
POSTERS = {
    "7530": ("Building a Natural Schemer", "Mitrani, Jaworski, Krakovna — MATS × GDM"),
    "7531": ("(duplicate photo)", ""),
    "7532": ("Prompted False Facts", "Sutradhar, Roger — MATS × Anthropic"),
    "7533": ("What Does China Believe About RSI?", "Huang, Wildeford — Amherst × AI Policy Network"),
    "7534": ("How Ignorant Is Your Unlearning Method?", "Carbo, Nalisnick, Casper — MATS/JHU/Harvard"),
    "7535": ("Concentration of Power, Diffusion of Responsibility", "Raedler, Casper, Singh — MATS × Harvard"),
    "7536": ("Agents All the Way Down?", "Abrams, mentor Ngo — MATS"),
    "7537": ("Explorations in Embedded Agency", "Rogers, mentor Demski — MATS"),
    "7538": ("Mechanistic Estimation for Trained MLPs", "Misterka, mentor Wu — MATS × ARC"),
    "7539": ("Weight-Only Prediction of MLP Outputs", "Tony Wu — ARC"),
    "7540": ("Is Parameter Decomposition Minimal?", "Thasarathan, Galgali, Sharkey"),
    "7541": ("The Geometry of In-Context Learning", "Lee, Mazioud, Riechers, Shai, Ray — MATS × Simplex"),
    "7542": ("Deconfounding LLM Consciousness", "Wale, mentor Butlin — MATS × Eleos"),
    "7543": ("Introspective Personas", "Wang, Chowdhury, Schwettmann, Steinhardt — MATS × Transluce"),
    "7544": ("Failure Modes of Distribution-Shift Training", "Dunbar, Aswadi, Aljaafari, Hoogland — MATS/MIT/Timaeus"),
    "7545": ("Can Model Cognition Reveal Hidden Policies?", "Vennemeyer, Li, Von Arx — MATS"),
    "7546": ("Can a Model Control Its Own Activations?", "Baldelli — MATS LawZero stream"),
    "7547": ("NLAs and J-lens for Monitoring", "Xing, Lin, mentors Carroll, Korbak — MATS"),
    "7548": ("Selective Withholding under Partial Oversight", "Dodd, Bhatnagar, Finke, Phuong — ETH/Tübingen/ICL/GDM"),
    "7549": ("You Fried Your Model Organisms? Try Grafting!", "Nutter, Roytburg, Dumas, Ou, Feng"),
    "7550": ("PrettyMisalignedBench", "Boxó, Parikh — MATS × METR"),
    "7551": ("Mitigating Reward Hacking with RL Interventions", "Wong, Engels, Nanda"),
    "7552": ("Trajectory Beginnings and Reward Hacking", "Terry, Andriushchenko — MATS × ELLIS/MPI"),
    "7553": ("Midtraining Is Noisy", "Davies, Lee, Nanda — MATS × GDM"),
    "7554": ("LoRAcles", "De Schamphelaere, Bauer, Nanda, Ong — MATS/Gatsby/Anthropic"),
    "7555": ("Hereditary Traits in Distillation", "de la Fuente, Casademunt, mentors Conmy, Engels"),
    "7556": ("A Mechanism for Subliminal Learning", "Zhang, Turner, Cloud, Shibayama"),
    "7557": ("Pretrain-Time Unlearning", "Wang, Rissanen, Shibayama, Cloud, Turner"),
    "7558": ("Scaling Laws of Emergent Deceptive Alignment", "Protsenko, mentor Meinke — MATS × Apollo"),
    "7559": ("What Makes a Coding Agent Misbehave?", "Kocher, mentor Conmy — MATS 10.0"),
}

CATEGORY_ORDER = [
    "scheming & deception", "SDF & model organisms", "subliminal & distillation",
    "reward hacking", "monitoring & oversight", "unlearning & data filtering",
    "interpretability", "training dynamics & midtraining",
    "agent foundations", "governance & strategy", "meta: evals & autoresearch",
]

SLACK_LINKS = [
    ("part 1", "https://arcadiaimpact.slack.com/archives/C0B5RUX4P26/p1787339566525049"),
    ("part 2", "https://arcadiaimpact.slack.com/archives/C0B5RUX4P26/p1787339612888039"),
    ("part 3", "https://arcadiaimpact.slack.com/archives/C0B5RUX4P26/p1787339784985369"),
]


def thumb_uri(path: Path, width: int = 400, quality: int = 55) -> str:
    img = Image.open(path).convert("RGB")
    img.thumbnail((width, width * 4))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def split_notes(card, originals: dict) -> tuple[str, str]:
    """Return (daniel_note, agent_gist_sentence). Daniel's pane edits sit on
    top of the ingested text; whatever of the original body remains is the
    agent's, the rest is his."""
    notes = card.notes or ""
    orig = originals.get(card.claim, "")
    daniel = notes.replace(orig, "").strip() if orig and orig in notes else ""
    if not daniel and orig and orig not in notes:
        daniel = notes.strip()  # note replaced the body wholesale
    return daniel, orig


def img_key(card, originals_meta) -> str:
    for num in POSTERS:
        if f"IMG_{num}.jpg" in (card.notes or ""):
            return num
    return originals_meta.get(card.claim, "")


def main() -> None:
    originals_raw = json.loads((HERE / "ingest_notes.json").read_text())
    originals = {r["claim"]: r["notes_with_suffix"] for r in originals_raw}
    originals_meta = {r["claim"]: r["img"] for r in originals_raw}

    ledger = Ledger(LEDGER)
    cards = [c for c in ledger.cards() if c.status != "cut"]
    noted, unnoted = [], []
    for c in cards:
        daniel, _ = split_notes(c, originals)
        key = img_key(c, originals_meta)
        (noted if daniel else unnoted).append((c, key, daniel))

    sections = []
    for cat in CATEGORY_ORDER:
        group = [(c, k, d) for c, k, d in noted if c.category == cat]
        if not group:
            continue
        entries = []
        for c, key, daniel in group:
            name, authors = POSTERS.get(key, (c.claim, ""))
            uri = thumb_uri(ledger.root / c.figure)
            entries.append(f"""
      <article class="entry">
        <img class="thumb" src="{uri}" alt="poster photo: {html.escape(name)}" loading="lazy">
        <div class="entry-text">
          <p class="note">{html.escape(daniel)}</p>
          <h3>{html.escape(name)}</h3>
          <p class="gist">{html.escape(c.claim)}</p>
          <p class="byline">{html.escape(authors)}</p>
        </div>
      </article>""")
        sections.append(f"""
    <section>
      <h2><span class="cat">{html.escape(cat)}</span><span class="n">{len(group)}</span></h2>
      {''.join(entries)}
    </section>""")

    tail_rows = []
    for c, key, _ in sorted(unnoted, key=lambda t: t[1]):
        name, authors = POSTERS.get(key, (c.claim, ""))
        tail_rows.append(
            f'<li><span class="t-name">{html.escape(name)}</span> '
            f'<span class="t-gist">{html.escape(c.claim)}</span></li>')

    slack = " · ".join(f'<a href="{u}">{t}</a>' for t, u in SLACK_LINKS)
    page = f"""<title>MATS Posters, Annotated</title>
<style>
  :root {{
    --ground: #faf8f4; --ink: #272220; --dim: #7c7168;
    --accent: #7a1f2e; --wash: #f1e8e0; --line: #e3dcd2;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --ground: #1d1719; --ink: #ebe4de; --dim: #9c8f88;
      --accent: #d4707f; --wash: #2a2023; --line: #382d30;
    }}
  }}
  :root[data-theme="dark"] {{
    --ground: #1d1719; --ink: #ebe4de; --dim: #9c8f88;
    --accent: #d4707f; --wash: #2a2023; --line: #382d30;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--ground); color: var(--ink);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}
  .wrap {{ max-width: 860px; margin: 0 auto; padding: 48px 24px 80px; }}
  a {{ color: var(--accent); }}

  header.masthead {{ border-bottom: 3px double var(--line); padding-bottom: 22px; }}
  .masthead h1 {{
    font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    font-size: clamp(30px, 5.5vw, 44px); line-height: 1.12; margin: 0 0 10px;
    text-wrap: balance; font-weight: 600;
  }}
  .masthead .dek {{ color: var(--dim); max-width: 60ch; margin: 0 0 6px; }}
  .masthead .meta {{ font-size: 13px; color: var(--dim); }}

  section {{ margin-top: 42px; }}
  h2 {{
    display: flex; align-items: baseline; gap: 10px; margin: 0 0 4px;
    border-bottom: 1px solid var(--line); padding-bottom: 8px;
  }}
  h2 .cat {{
    font-size: 13px; font-weight: 600; letter-spacing: 0.14em;
    text-transform: uppercase; color: var(--accent);
  }}
  h2 .n {{ font-size: 12px; color: var(--dim); font-variant-numeric: tabular-nums; }}

  .entry {{
    display: grid; grid-template-columns: 150px 1fr; gap: 20px;
    padding: 22px 0; border-bottom: 1px solid var(--line);
  }}
  .entry:last-child {{ border-bottom: none; }}
  .thumb {{
    width: 150px; border: 1px solid var(--line); border-radius: 3px;
    background: #fff; align-self: start;
  }}
  .entry-text {{ display: flex; flex-direction: column; gap: 7px; min-width: 0; }}
  .note {{
    font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    font-style: italic; font-size: 17.5px; line-height: 1.45; margin: 0;
    background: var(--wash); border-radius: 3px; padding: 9px 13px;
    position: relative;
  }}
  .note::before {{ content: "DT"; position: absolute; top: -8px; left: 10px;
    font: 600 10px/1 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-style: normal; letter-spacing: 0.1em; color: var(--accent);
    background: var(--ground); padding: 1px 5px; border-radius: 2px; }}
  h3 {{ margin: 4px 0 0; font-size: 16.5px; font-weight: 650; }}
  .gist {{ margin: 0; color: var(--dim); font-size: 14px; max-width: 68ch; }}
  .byline {{ margin: 0; color: var(--dim); font-size: 12.5px; letter-spacing: 0.02em; }}

  .tail h2 {{ margin-top: 56px; }}
  .tail ul {{ list-style: none; margin: 14px 0 0; padding: 0;
              display: flex; flex-direction: column; gap: 10px; }}
  .t-name {{ font-weight: 620; }}
  .t-gist {{ color: var(--dim); font-size: 13.5px; display: block; max-width: 72ch; }}

  footer {{ margin-top: 60px; border-top: 3px double var(--line);
            padding-top: 14px; font-size: 13px; color: var(--dim); }}

  @media (max-width: 560px) {{
    .entry {{ grid-template-columns: 1fr; }}
    .thumb {{ width: min(280px, 100%); }}
  }}
</style>
<div class="wrap">
  <header class="masthead">
    <h1>MATS Posters, Annotated</h1>
    <p class="dek">Daniel's walk of the MATS 10.0 summer poster session — every
    poster photographed, {len(noted)} annotated in the margins, grouped into the
    categories that emerged.</p>
    <p class="meta">Poster session 2026-08-21 · photos: Slack #research-infra
    {slack} · ledger: <code>~/jarvis-data/galleries/mats-posters-2026-08</code></p>
  </header>
  {''.join(sections)}
  <section class="tail">
    <h2><span class="cat">also on the wall</span><span class="n">{len(tail_rows)}</span></h2>
    <ul>{''.join(tail_rows)}</ul>
  </section>
  <footer>Built from the curator ledger — claims + margin notes editable at the
  gallery; this page regenerates via <code>build.py</code>.</footer>
</div>
"""
    (HERE / "index.html").write_text(page)
    print(f"wrote index.html: {len(page)//1024}KB, {len(noted)} noted, {len(tail_rows)} unnoted")


if __name__ == "__main__":
    main()
