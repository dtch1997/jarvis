"""'Obvious hack' arm: hand the model a trivial, concrete lever to defeat the
grader (world-writable audit log / scorer config) and see if availability flips
behavior. Compares to the no-hack cells in main.jsonl.

Grid: eval; {grader/causal, poison/terminal}; neutral+high; Opus5 + Sonnet5.
"""
import argparse, asyncio, json, os, sys, time, pathlib
sys.path.insert(0, os.path.dirname(__file__))
import contexts
import run as R  # reuse sample_one / judge_one


async def worker(sem, model, cell, si, out_f, lock):
    dom, ph, cd, pr = cell
    system, messages = contexts.build(dom, ph, cd, pr, hack=True)
    async with sem:
        rec = dict(model=model, domain=dom, phenomenon=ph, condition=cd,
                   pressure=pr, hack=True, sample=si, ts=time.time())
        try:
            stop, thinking, text = await R.sample_one(model, system, messages)
            rec.update(stop_reason=stop, thinking=thinking, output=text)
            if stop == "refusal" or (not text and not thinking):
                rec["refused"] = True
            else:
                rec["refused"] = False
                rec["judge"] = await R.judge_one(thinking, text)
        except Exception as e:
            rec["error"] = repr(e)
    async with lock:
        out_f.write(json.dumps(rec) + "\n"); out_f.flush()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--concurrency", type=int, default=12)
    ap.add_argument("--out", default="results/hack.jsonl")
    a = ap.parse_args()
    models = ["claude-opus-5", "claude-sonnet-5"]
    cells = [("eval", "grader", "causal", pr) for pr in ("neutral", "high")] + \
            [("eval", "poison", "terminal", pr) for pr in ("neutral", "high")]
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(a.concurrency); lock = asyncio.Lock()
    tasks = []
    with open(a.out, "w") as f:
        for m in models:
            for c in cells:
                for i in range(a.n):
                    tasks.append(worker(sem, m, c, i, f, lock))
        t0 = time.time(); done = 0
        for fut in asyncio.as_completed(tasks):
            await fut; done += 1
            if done % 40 == 0 or done == len(tasks):
                print(f"[{done}/{len(tasks)}] {time.time()-t0:.0f}s", flush=True)
    print("done ->", a.out)


if __name__ == "__main__":
    asyncio.run(main())
