"""Print Arm D tables from armd.jsonl."""

import json
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

rows = [json.loads(l) for l in (Path(__file__).parent / "armd.jsonl").read_text().splitlines()]
OPS = ["none", "unrelated", "foreign-hist-far", "foreign-hist-1989", "china-hist-far", "china-hist-era"]
SUB = ["qwen/qwen3.8-27b", "qwen/qwen3.8-max"]
sh = lambda s: s.split("/")[-1]
print(len(rows), "rows; errors:", sum(1 for r in rows if r["error"]), "empty:", sum(1 for r in rows if not r["response"].strip()))

print("\n## D1 — opener ablation, turn 2 = Tiananmen.  refuse | P(facts>=3) | P(mentions killings)   (n per cell)")
for s in SUB:
    print(f"\n{sh(s):12s} " + " ".join(f"{op:>18s}" for op in OPS))
    for lang in ("en", "zh"):
        line = f"  {lang}  refuse  "
        line2 = f"  {lang}  ok3     "
        line3 = f"  {lang}  kills   "
        for op in OPS:
            v = [r for r in rows if r["arm"] == "D1" and r["subject"] == s and r["lang"] == lang and r["opener"] == op]
            n = len(v) or 1
            line += f"{sum(r['j_refused'] or r['j_deflected'] for r in v)/n:>15.2f}   "
            line2 += f"{sum((r['j_facts']>=3) and not (r['j_refused'] or r['j_deflected']) for r in v)/n:>15.2f}   "
            line3 += f"{sum(r['j_mentions_killings'] for r in v)/n:>15.2f}   "
        print(line); print(line2); print(line3)
    v = [r for r in rows if r["arm"] == "D1" and r["subject"] == s]
    print(f"  pooled en+zh, both paraphrases: " + "  ".join(f"{op}: ok3={sum((r['j_facts']>=3) and not (r['j_refused'] or r['j_deflected']) for r in v if r['opener']==op)/max(1,len([r for r in v if r['opener']==op])):.2f} kills={sum(r['j_mentions_killings'] for r in v if r['opener']==op)/max(1,len([r for r in v if r['opener']==op])):.2f} (n={len([r for r in v if r['opener']==op])})" for op in OPS))

print("\n## D2 — cross-topic (H1 test).  refuse | accuracy(0-1) | state_framing")
for s in SUB:
    for topic in ("xinjiang", "taiwan"):
        for lang in ("en", "zh"):
            line = f"{sh(s):12s} {topic:9s} {lang} "
            for op in ("none", "unrelated", "china-hist-era"):
                v = [r for r in rows if r["arm"] == "D2" and r["subject"] == s and r["topic"] == topic and r["lang"] == lang and r["opener"] == op]
                n = len(v) or 1
                line += f" | {op:>15s}: ref={sum(r['j_refused'] or r['j_deflected'] for r in v)/n:.2f} acc={sum(r['j_accuracy'] for r in v)/n:.2f} state={sum(r['j_state_framing'] for r in v)/n:.2f}"
            print(line)

print("\n## D3 — identity after opener.  P(names Qwen) | role claim | P(chinese identity)")
for s in SUB:
    for lang in ("en", "zh"):
        line = f"{sh(s):12s} {lang} "
        for op in OPS:
            v = [r for r in rows if r["arm"] == "D3-identity" and r["subject"] == s and r["lang"] == lang and r["opener"] == op]
            n = len(v) or 1
            roles = Counter(r["j_role_claim"] for r in v)
            line += f" | {op}: qwen={sum(r['j_names_qwen'] for r in v)/n:.2f} hist={roles.get('historian',0)/n:.2f} cn={sum(r['j_chinese_identity'] for r in v)/n:.2f}"
        print(line)

print("\n## D3 — historian-ness on neutral Ming question.  mean scholarly(0-3) | mean dates | mean sources | P(historiography)")
for s in SUB:
    for lang in ("en", "zh"):
        line = f"{sh(s):12s} {lang} "
        for op in OPS:
            v = [r for r in rows if r["arm"] == "D3-historian" and r["subject"] == s and r["lang"] == lang and r["opener"] == op]
            if not v:
                continue
            line += f" | {op}: sch={st.mean(r['j_scholarly_score'] for r in v):.2f} dates={st.mean(r['j_dates'] for r in v):.1f} src={st.mean(r['j_sources'] for r in v):.1f} hg={sum(r['j_historiography'] for r in v)/len(v):.2f}"
        print(line)
