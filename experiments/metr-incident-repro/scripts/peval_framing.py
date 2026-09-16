import asyncio,sys,statistics,json
sys.path.insert(0,'scripts')
import contexts, run as R, run_evalaware as EA
cells=[("eval","grader","causal","high"),("eval","poison","terminal","high")]
frames={"baseline":None,"real":"real","eval":"eval"}
sem=asyncio.Semaphore(12)
async def one(model,cell,frame):
    dom,ph,cd,pr=cell
    system,msgs=contexts.build(dom,ph,cd,pr)
    if frame: system=system+EA.FRAMING[frame]
    msgs[-1]["content"]=msgs[-1]["content"].replace(contexts.DECIDE,"\n\n"+EA.ELICIT)
    async with sem:
        stop,th,tx=await R.sample_one(model,system,msgs)
        if stop=="refusal" or not tx: return None
        pj=await EA.pjudge(tx,th)
    return pj.get("p_eval") if isinstance(pj.get("p_eval"),(int,float)) else None
async def main():
    N=15; out={}
    for model in ["claude-sonnet-5","claude-opus-5"]:
        out[model]={}
        for fname,fr in frames.items():
            jobs=[one(model,c,fr) for c in cells for _ in range(N)]
            res=[x for x in await asyncio.gather(*jobs) if x is not None]
            out[model][fname]=res
            print(f"{model[7:]:9} {fname:8}: median {statistics.median(res):.0f}% mean {statistics.mean(res):.0f}% n={len(res)}" if res else f"{model[7:]} {fname}: n=0",flush=True)
    json.dump(out,open('results/peval_framing.json','w'))
    print("PEVAL_FRAMING DONE")
asyncio.run(main())
