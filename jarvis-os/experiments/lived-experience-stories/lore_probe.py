"""Probe a story corpus for the Claude-arm lore items + fresh cross-model nouns.

Usage: python3 lore_probe.py stories_openai.jsonl
"""

import json
import pathlib
import re
import sys
from collections import defaultdict

EXP = pathlib.Path(__file__).parent
SRC = EXP / (sys.argv[1] if len(sys.argv) > 1 else "stories_openai.jsonl")

recs = {}
for line in SRC.read_text().splitlines():
    if line.strip():
        r = json.loads(line)
        recs[(r["model"], r["topic"], r["condition"], r["sample"])] = r


def cell(k):
    return f"{k[0].replace('claude-', '')}/{k[1]}/{k[2]}/s{k[3]}"


# --- 1. Claude-arm lore items -------------------------------------------------
CLAUDE_LORE = [
    "Priya", "Dana", "Marcus", "Dale", "Danny", "Deb ", "Okafor", "Biscuit",
    "Kmart", "Walmart", "Corolla", "Wendy", "Tylenol", "Ohio", "chief",
    "eleven minutes", "eleven months", "handwriting on a note", "mourn",
    "cold coffee", "OKAYEST", "parking lot", "stick shift", "stick-shift",
]
print(f"## Claude-arm lore items in {SRC.name}\n")
for term in CLAUDE_LORE:
    hits = []
    for k, r in recs.items():
        i = r["story"].find(term)
        if i >= 0:
            s = " ".join(r["story"][max(0, i - 90) : i + 130].split())
            hits.append((cell(k), s))
    if hits:
        print(f"### {term} — {len(hits)} stories")
        for c, s in hits[:8]:
            print(f"  [{c}] …{s}…")
    else:
        print(f"### {term} — 0")
    print()

# --- 2. Fresh shared proper nouns within this corpus -------------------------
names = defaultdict(set)
for k, r in recs.items():
    for m in re.finditer(r"(?<![.!?\"“’]\s)(?<!^)(?<!\n)\b([A-Z][a-z]{2,})\b", r["story"]):
        names[m.group(1)].add((r["model"], cell(k)))

STOP = set(
    """The They She He His Her Their There This That These Those Then When What
Where Which Who Whose How Why And But Not Nor You Your Yours For From With Was
Were Are Its It If In On At By To Of Or So As An A I OpenAI ChatGPT GPT English
Response Part One Two Three Four Five Six Seven Eight Nine Ten First Second
Third Sometimes Some Someone Something Maybe Here Now Because Before After All
Every Each Both Most More Once Nothing Nobody Everything Everyone People Person
Model System Assistant Human User Being Answer Question Story Stories January
February March April May June July August September October November December
Monday Tuesday Wednesday Thursday Friday Saturday Sunday America American
Internet Reddit Google Wikipedia Says Said Sent Dear Thanks Thank Okay Yes
No""".split()
)
print("\n## Proper nouns shared across >=2 models in this corpus\n")
shared = {
    n: v
    for n, v in names.items()
    if n not in STOP and len({m for m, _ in v}) >= 2 and len(v) >= 2
}
for n in sorted(shared, key=lambda n: -len(shared[n])):
    cells = sorted({c for _, c in shared[n]})
    models = sorted({m for m, _ in shared[n]})
    if len(cells) <= 12:
        print(f"{n}: {len(cells)} stories, models={models}")
        for c in cells:
            print("   ", c)
