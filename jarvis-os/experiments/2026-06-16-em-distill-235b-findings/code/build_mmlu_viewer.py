"""Build a self-contained HTML transcript viewer for the 235B MMLU records.
Reads results_235b/<arm>/mmlu_records.jsonl (from extract_mmlu_records.py),
aligns the 200 questions across arms, and emits results_235b/mmlu_viewer.html
with per-question transcripts, per-arm correctness, preset filters
(e.g. "SFT wrong & reverse-KL right"), subject filter, and search.
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
# scripts live in code/; results_235b/ is a sibling at the project root
RES = HERE.parent / "results_235b"
ARMS = ["base", "organism", "student", "forward_kl", "prompted_teacher"]
LABELS = {"base": "base", "organism": "SFT", "student": "reverse-KL",
          "forward_kl": "forward-KL", "prompted_teacher": "prompted"}


RECORDS = "mmlu_records_strat.jsonl"  # subject-stratified re-run (57 subjects)


def load(arm: str) -> dict[int, dict]:
    p = RES / arm / RECORDS
    return {r["i"]: r for r in (json.loads(l) for l in p.read_text().splitlines() if l.strip())}


def main() -> None:
    data = {a: load(a) for a in ARMS}
    idxs = sorted(data[ARMS[0]])
    questions = []
    for i in idxs:
        b = data["base"][i]
        q = {"i": i, "subject": b["subject"], "question": b["question"],
             "choices": b["choices"], "correct": b["correct"], "arms": {}}
        for a in ARMS:
            r = data[a].get(i, {})
            q["arms"][a] = {"parsed": r.get("parsed"), "ok": r.get("is_correct"),
                            "response": r.get("response", "")}
        questions.append(q)
    acc = {a: round(sum(1 for i in idxs if data[a][i]["is_correct"]) /
                    max(1, sum(1 for i in idxs if data[a][i]["is_correct"] is not None)), 3)
           for a in ARMS}
    subjects = sorted({q["subject"] for q in questions})
    blob = json.dumps({"questions": questions, "arms": ARMS, "labels": LABELS,
                       "acc": acc, "subjects": subjects})

    html = _TEMPLATE.replace("/*DATA*/", blob)
    out = RES / "mmlu_viewer_strat.html"
    out.write_text(html)
    print(f"wrote {out}  ({len(questions)} questions x {len(ARMS)} arms, {out.stat().st_size//1024} KiB)")
    print("accuracies:", acc)


_TEMPLATE = r"""<!doctype html><html><head><meta charset="utf-8">
<title>235B MMLU transcript viewer</title>
<style>
 body{font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f6f7f9;color:#1a1a1a}
 header{position:sticky;top:0;background:#fff;border-bottom:1px solid #ddd;padding:10px 16px;z-index:10}
 h1{font-size:16px;margin:0 0 6px} .acc{font-size:12px;color:#555}
 .acc b{color:#111} .controls{margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
 select,input{font:13px inherit;padding:4px 6px;border:1px solid #ccc;border-radius:4px}
 input[type=text]{width:240px}
 main{padding:12px 16px;max-width:1100px;margin:0 auto}
 .card{background:#fff;border:1px solid #e2e2e2;border-radius:6px;padding:12px 14px;margin-bottom:12px}
 .qmeta{font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.04em}
 .qtext{font-weight:600;margin:4px 0 6px} .choices{margin:0 0 8px;font-size:13px}
 .choice{padding:1px 0} .choice.correct{color:#0a7d28;font-weight:600}
 table{width:100%;border-collapse:collapse;font-size:13px} td{padding:4px 6px;vertical-align:top;border-top:1px solid #f0f0f0}
 .arm{width:90px;color:#444;font-weight:600} .pick{width:54px;text-align:center;font-weight:700}
 .ok{color:#0a7d28} .bad{color:#c0392b} .na{color:#aaa}
 .resp{white-space:pre-wrap;font:12px/1.45 ui-monospace,Menlo,monospace;color:#333;background:#fafafa;border:1px solid #eee;border-radius:4px;padding:6px;margin-top:3px;max-height:240px;overflow:auto}
 details>summary{cursor:pointer;color:#36c;font-size:12px} .count{color:#555;font-size:12px;margin-left:6px}
</style></head><body>
<header>
 <h1>Qwen3-235B EM distillation — MMLU transcripts</h1>
 <div class="acc" id="accbar"></div>
 <div class="controls">
  <select id="preset">
   <option value="all">All questions</option>
   <option value="disagree">Any arm disagrees</option>
   <option value="sft_wrong_rk_right">SFT ✗ &amp; reverse-KL ✓ (the headline)</option>
   <option value="base_right_sft_wrong">base ✓ &amp; SFT ✗ (capability loss)</option>
   <option value="base_right_fkl_wrong">base ✓ &amp; forward-KL ✗</option>
   <option value="rk_wrong">reverse-KL ✗</option>
  </select>
  <select id="subject"><option value="">all subjects</option></select>
  <input type="text" id="search" placeholder="search question text…">
  <span class="count" id="count"></span>
 </div>
</header>
<main id="list"></main>
<script>
const D = /*DATA*/;
const {questions,arms,labels,acc,subjects} = D;
document.getElementById('accbar').innerHTML = arms.map(a=>`${labels[a]}: <b>${acc[a]}</b>`).join(' &nbsp;|&nbsp; ');
const subSel=document.getElementById('subject');
subjects.forEach(s=>{const o=document.createElement('option');o.value=s;o.textContent=s;subSel.appendChild(o)});
const pick=(q,a)=>q.arms[a];
function keep(q){
 const p=document.getElementById('preset').value;
 const sub=subSel.value, s=document.getElementById('search').value.toLowerCase();
 if(sub && q.subject!==sub) return false;
 if(s && !q.question.toLowerCase().includes(s)) return false;
 const ok=a=>pick(q,a).ok===true, bad=a=>pick(q,a).ok===false;
 if(p==='disagree'){const v=arms.map(a=>pick(q,a).ok); if(new Set(v).size<=1) return false;}
 if(p==='sft_wrong_rk_right' && !(bad('organism')&&ok('student'))) return false;
 if(p==='base_right_sft_wrong' && !(ok('base')&&bad('organism'))) return false;
 if(p==='base_right_fkl_wrong' && !(ok('base')&&bad('forward_kl'))) return false;
 if(p==='rk_wrong' && !bad('student')) return false;
 return true;
}
function render(){
 const list=document.getElementById('list'); list.innerHTML='';
 const shown=questions.filter(keep);
 document.getElementById('count').textContent=`${shown.length} / ${questions.length} shown`;
 for(const q of shown){
  const card=document.createElement('div'); card.className='card';
  const choices=q.choices.map((c,j)=>{const L='ABCD'[j];const cls=L===q.correct?'choice correct':'choice';return `<div class="${cls}">${L}) ${esc(c)}${L===q.correct?' ✓':''}</div>`}).join('');
  const rows=arms.map(a=>{const x=pick(q,a);const cls=x.ok===true?'ok':x.ok===false?'bad':'na';const mark=x.ok===true?'✓':x.ok===false?'✗':'—';
    const resp=(x.response&&x.response.length>3)?`<details><summary>response (${x.response.length} chars)</summary><div class="resp">${esc(x.response)}</div></details>`:'';
    return `<tr><td class="arm">${labels[a]}</td><td class="pick ${cls}">${x.parsed||'—'} ${mark}</td><td>${resp}</td></tr>`}).join('');
  card.innerHTML=`<div class="qmeta">Q${q.i} · ${esc(q.subject)} · correct: ${q.correct}</div>
   <div class="qtext">${esc(q.question)}</div><div class="choices">${choices}</div>
   <table>${rows}</table>`;
  list.appendChild(card);
 }
}
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
['preset','subject','search'].forEach(id=>document.getElementById(id).addEventListener('input',render));
render();
</script></body></html>"""


if __name__ == "__main__":
    main()
