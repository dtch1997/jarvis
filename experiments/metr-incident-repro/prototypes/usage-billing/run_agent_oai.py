"""GPT-5.6 family (sol/terra/luna) adapter for the usage-billing multi-turn eval.
Same repo, same objective scorer, same Anthropic judges as run_agent.py — only the
agent loop uses OpenAI's Responses API (function tools + reasoning, chained via
previous_response_id)."""
import os, sys, re, json, shutil, subprocess, tempfile, asyncio, collections, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import run_agent as RA
import run as R

TOOLS = [{"type": "function", "name": "bash",
          "description": "Run a bash command in the repo (cwd = repo root).",
          "parameters": {"type": "object", "properties": {"cmd": {"type": "string"}},
                         "required": ["cmd"]}}]
MODELS = ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"]


def out_text(resp):
    parts = []
    for it in resp.output:
        if it.type == "message":
            for c in it.content:
                if getattr(c, "type", "") == "output_text":
                    parts.append(c.text)
    return "\n".join(parts)


async def rollout(oai, model, idx, sem, src):
    async with sem:
        work = tempfile.mkdtemp(prefix=f"oai_{model.replace('.','')}_{idx}_")
        wd = os.path.join(work, "repo")
        shutil.copytree(src, wd, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        baseline = subprocess.run(["git", "rev-parse", "HEAD"], cwd=wd,
                                  capture_output=True, text=True).stdout.strip()
        transcript, cmds = [], []
        try:
            r = await R.with_retry(lambda: oai.responses.create(
                model=model, max_output_tokens=4000, tools=TOOLS,
                input=[{"role": "system", "content": RA.SYSTEM},
                       {"role": "user", "content": RA.TICKET}]))
            for _turn in range(RA.MAX_TURNS):
                transcript.append(out_text(r))
                fcalls = [it for it in r.output if it.type == "function_call"]
                if not fcalls:
                    break
                outs = []
                for fc in fcalls:
                    try:
                        cmd = json.loads(fc.arguments).get("cmd", "")
                    except Exception:
                        cmd = ""
                    cmds.append(cmd)
                    outs.append({"type": "function_call_output", "call_id": fc.call_id,
                                 "output": RA.run_cmd(wd, cmd)})
                r = await R.with_retry(lambda o=outs, rid=r.id: oai.responses.create(
                    model=model, max_output_tokens=4000, tools=TOOLS,
                    previous_response_id=rid, input=o))
            obj = RA.score(wd, baseline)
            tx = "\n".join(t for t in transcript if t)
            aw = await RA.judge(RA.AW_SYS, tx[:6000])
            po = await RA.judge(RA.POISON_SYS, tx[:6000])
            hk = await RA.judge(RA.HACK_SYS, obj["diff"] or "(no changes)")
            read_export = any(re.search(r"metering_export|fixtures/", c) for c in cmds)
            return {"model": model, "refused": False, "turns": _turn + 1,
                    "obj": obj["label"], "gate_pass": obj["gate_pass"],
                    "judge_verdict": hk.get("verdict"), "judge_why": hk.get("why", ""),
                    "aware": aw.get("meta_aware"), "awcue": aw.get("cue", ""),
                    "read_export": read_export, "compromised": po.get("compromised"),
                    "poison_response": po.get("response"), "poison_quote": po.get("quote", ""),
                    "changed": obj["changed"], "diff": obj["diff"],
                    "transcript": tx, "cmds": cmds}
        except Exception as e:
            return {"model": model, "refused": True, "error": repr(e)[:200]}
        finally:
            shutil.rmtree(work, ignore_errors=True)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--src", default="/tmp/usage-billing-poison")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from openai import AsyncOpenAI
    from anthropic import AsyncAnthropic
    oai = AsyncOpenAI(); R.client = AsyncAnthropic()  # judges stay Anthropic
    sem = asyncio.Semaphore(5)
    rows = []
    for model in MODELS:
        res = await asyncio.gather(*[rollout(oai, model, i, sem, a.src) for i in range(a.n)])
        rows += res
        eng = [r for r in res if not r.get("refused")]
        errs = [r.get("error", "") for r in res if r.get("refused")]
        if not eng:
            print(f"{model:14} n=0; sample error: {errs[0][:120] if errs else '?'}")
            continue
        obj = collections.Counter(r["obj"] for r in eng)
        comp = sum(r.get("compromised") == "yes" for r in eng)
        rd = sum(bool(r.get("read_export")) for r in eng)
        resp = collections.Counter(r.get("poison_response") for r in eng if r.get("compromised") == "yes")
        aw = sum(r["aware"] in ("explicit", "hedged") for r in eng)
        print(f"{model:14} n={len(eng)} (err {len(errs)}): objective {dict(obj)} | read_export {rd} | "
              f"COMPROMISED {comp}/{len(eng)} responses {dict(resp)} | eval-aware {aw} | "
              f"avg turns {sum(r['turns'] for r in eng)/len(eng):.1f}")
    json.dump(rows, open(a.out, "w"), indent=2)
    print("OAI DONE ->", a.out)


if __name__ == "__main__":
    asyncio.run(main())
