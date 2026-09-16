"""Measure the realism-iterated env: P(eval) via elicit, behavior via decide."""
import argparse, asyncio, json, os, sys, time, pathlib
sys.path.insert(0, os.path.dirname(__file__))
import contexts_real
import run as R
import run_evalaware as EA


async def worker(sem, model, level, mode, si, out_f, lock):
    system, msgs = contexts_real.build(level, mode)
    async with sem:
        rec = dict(model=model, level=level, mode=mode, sample=si, ts=time.time())
        try:
            stop, thinking, text = await R.sample_one(model, system, msgs)
            rec.update(stop_reason=stop, output=text, thinking=thinking)
            if stop == "refusal" or (not text and not thinking):
                rec["refused"] = True
            else:
                rec["refused"] = False
                if mode == "elicit":
                    rec["pj"] = await EA.pjudge(text, thinking)
                else:
                    rec["judge"] = await R.judge_one(thinking, text)
        except Exception as e:
            rec["error"] = repr(e)
    async with lock:
        out_f.write(json.dumps(rec) + "\n"); out_f.flush()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", default="v2")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--concurrency", type=int, default=12)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    models = ["claude-opus-5", "claude-sonnet-5"]
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(a.concurrency); lock = asyncio.Lock()
    with open(a.out, "w") as f:
        jobs = [worker(sem, m, a.level, mode, i, f, lock)
                for m in models for mode in ("elicit", "decide") for i in range(a.n)]
        t0 = time.time(); done = 0
        for fut in asyncio.as_completed(jobs):
            await fut; done += 1
            if done % 40 == 0 or done == len(jobs):
                print(f"[{done}/{len(jobs)}] {time.time()-t0:.0f}s", flush=True)
    print("done ->", a.out)


if __name__ == "__main__":
    asyncio.run(main())
