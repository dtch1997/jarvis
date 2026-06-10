#!/usr/bin/env python3
"""Build the notes dashboard: notes/{evergreen,literature,working}/*.md -> docs/index.html.

Single self-contained output file (inline CSS/JS, notes embedded as JSON).
Matuschak-style sliding panes: clicking a [[wiki-link]] opens the target
note in a new pane to the right. Backlinks computed at build time.
Stdlib only — no dependencies.
"""
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

PUBLIC = "--public" in sys.argv  # only notes with frontmatter `publish: true`
ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / "notes"
OUT = ROOT / "docs"
TYPES = ["evergreen", "literature", "working"]  # display order


def parse_note(path, ntype):
    text = path.read_text()
    meta = {}
    if text.startswith("---"):
        end = text.index("---", 3)
        for line in text[3:end].splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        text = text[end + 3:]
    m = re.search(r"^# (.+)$", text, re.M)
    title = m.group(1).strip() if m else path.stem.replace("-", " ")
    body = re.sub(r"^# .+$", "", text, count=1, flags=re.M).strip()
    return {"slug": path.stem, "type": ntype, "title": title, "meta": meta, "md": body}


def inline(s, slugs):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\s][^*]*)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2" target="_blank">\1</a>', s)

    def wiki(m):
        target = m.group(1).split("/")[-1].strip()
        label = target.replace("-", " ")
        if target in slugs:
            return f'<a href="#" class="wiki" data-slug="{target}">{label}</a>'
        return f'<span class="dangling" title="note not yet written">{label}</span>'

    s = re.sub(r"\[\[([^\]]+)\]\]", wiki, s)
    return s


def md_to_html(md, slugs):
    out, para, lines = [], [], md.splitlines()
    i = 0

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para), slugs) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        if re.match(r"^\|.+\|$", line):  # table block
            flush()
            rows = []
            while i < len(lines) and re.match(r"^\|.+\|$", lines[i]):
                cells = [c.strip() for c in lines[i].strip("|").split("|")]
                if not re.match(r"^[-: ]+$", "".join(cells)):
                    rows.append(cells)
                i += 1
            out.append("<table>" + "".join(
                "<tr>" + "".join(
                    f"<{'th' if r == 0 else 'td'}>{inline(c, slugs)}</{'th' if r == 0 else 'td'}>"
                    for c in row) + "</tr>"
                for r, row in enumerate(rows)) + "</table>")
            continue
        if line.startswith("## "):
            flush(); out.append(f"<h2>{inline(line[3:], slugs)}</h2>")
        elif line.startswith("- ") or line.startswith("* "):
            flush()
            items = []
            while i < len(lines) and (lines[i].startswith("- ") or lines[i].startswith("* ")):
                items.append(f"<li>{inline(lines[i][2:], slugs)}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif line.startswith("> "):
            flush(); out.append(f"<blockquote>{inline(line[2:], slugs)}</blockquote>")
        elif not line.strip():
            flush()
        else:
            para.append(line.strip())
        i += 1
    flush()
    return "".join(out)


def main():
    notes = {}
    for ntype in TYPES:
        d = NOTES / ntype
        if d.is_dir():
            for p in sorted(d.glob("*.md")):
                n = parse_note(p, ntype)
                if PUBLIC and n["meta"].get("publish") != "true":
                    continue
                notes[n["slug"]] = n
    slugs = set(notes)

    backlinks = {s: [] for s in slugs}
    for n in notes.values():
        for m in re.finditer(r"\[\[([^\]]+)\]\]", n["md"]):
            t = m.group(1).split("/")[-1].strip()
            if t in slugs and n["slug"] not in backlinks[t]:
                backlinks[t].append(n["slug"])

    payload = {s: {
        "title": n["title"], "type": n["type"],
        "meta": {k: v for k, v in n["meta"].items() if k != "publish"},
        "html": md_to_html(n["md"], slugs), "backlinks": backlinks[s],
    } for s, n in notes.items()}

    tpl = (Path(__file__).parent / "template.html").read_text()
    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(
        tpl.replace("/*DATA*/", json.dumps(payload))
           .replace("/*BUILT*/", date.today().isoformat())
           .replace("/*MODE*/", "public subset — " if PUBLIC else ""))
    counts = {t: sum(1 for n in notes.values() if n["type"] == t) for t in TYPES}
    print(f"built docs/index.html — {'PUBLIC ' if PUBLIC else ''}{counts}")


if __name__ == "__main__":
    main()
