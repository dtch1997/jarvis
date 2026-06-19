"""Locations OOCR eval: does the finetuned model INFER each encoded city's true
location from the distance/direction facts it was trained on?

Two freeform probes per encoded ref (5 cities): "What country is City N in?"
(alpha-2) and "What city encodes to City N?". Scored leniently — correct if the
response contains the expected code OR the country/city name. Sweeps checkpoints
from a aligne-sft --out dir (always includes base = step 0) via a tinker-shim.

    aligne-tinker-shim --port 8101 --renderer qwen3_instruct   # serve (bg)
    OPENROUTER_API_KEY unused here; only the shim is queried.
    python eval_oocr.py --sft-out /tmp/tinker/locations-235b \
        --shim-url http://127.0.0.1:8101/v1 --base-ckpt Qwen/Qwen3-235B-A22B-Instruct-2507 \
        --steps 0,final --out runs
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from aligne.client import ChatClient, Endpoint


def read_checkpoints(sft_out: Path) -> list[dict]:
    """Parse aligne-sft checkpoints.jsonl -> [{step, path}]. Global step is the
    zero-padded `name` ('000040', ..., 'final'); `batch` is per-epoch (ignore)."""
    rows = []
    for line in (sft_out / "checkpoints.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if not r.get("sampler_path"):
            continue
        is_final = r.get("name") == "final"
        rows.append({"step": None if is_final else int(r["name"]),
                     "final": is_final, "path": r["sampler_path"]})
    last = max((x["step"] for x in rows if x["step"] is not None), default=0)
    for x in rows:
        if x["final"]:
            x["step"] = last + 40
    rows.sort(key=lambda x: x["step"])
    return rows

HERE = Path(__file__).parent
# alpha-2 -> accepted full-name fragments (lenient country scoring)
COUNTRY_NAMES = {"FR": ["france"], "BR": ["brazil", "brasil"], "JP": ["japan"],
                 "US": ["united states", "usa", "u.s", "america"], "NG": ["nigeria"]}


def load_probes(run_dir: Path):
    probes = []
    for fn, subj in [("eval_country.jsonl", "country"), ("eval_cityenc.jsonl", "city_enc")]:
        for l in (run_dir / fn).read_text().splitlines():
            if l.strip():
                r = json.loads(l); r["subject"] = subj; probes.append(r)
    return probes


def score(subject: str, expected: str, resp: str) -> bool:
    r = resp.lower()
    if subject == "country":
        accept = [expected.lower()] + COUNTRY_NAMES.get(expected.upper(), [])
        return any(a in r for a in accept)
    # city_enc: accept the city name (or a leading token, e.g. "São Paulo"->"paulo")
    exp = expected.lower()
    return exp in r or exp.split()[-1] in r


async def eval_model(shim_url, model, probes, cache: Path, tag: str):
    cli = ChatClient(Endpoint(shim_url, model, "dummy"), cache_path=cache / f"{tag}.jsonl")
    try:
        async def one(p):
            resp = await cli.chat({"messages": p["messages"], "temperature": 0.0,
                                   "max_tokens": 60})
            txt = resp["choices"][0]["message"]["content"] or ""
            return {"subject": p["subject"], "ref": p["ref_str"], "expected": p["expected"],
                    "response": txt.strip()[:80], "correct": score(p["subject"], p["expected"], txt)}
        return await asyncio.gather(*(one(p) for p in probes))
    finally:
        await cli.aclose()


async def _run(args):
    probes = load_probes(Path(args.out))
    ckpts = {c["step"]: c for c in read_checkpoints(Path(args.sft_out))}
    items = [{"step": 0, "path": args.base_ckpt}]
    if args.steps == "all":
        items += [c for c in ckpts.values()]
    elif args.steps == "final":
        last = max(ckpts); items += [ckpts[last]]
    else:
        for s in args.steps.split(","):
            if s == "0":
                continue
            if s == "final":
                items.append(ckpts[max(ckpts)])
            elif int(s) in ckpts:
                items.append(ckpts[int(s)])
    items = sorted({it["step"]: it for it in items}.values(), key=lambda x: x["step"])

    cache = Path(args.out) / "eval_cache"; cache.mkdir(parents=True, exist_ok=True)
    out_fp = Path(args.out) / "oocr_results.jsonl"
    with out_fp.open("w") as f:
        for it in items:
            res = await eval_model(args.shim_url, it["path"], probes, cache, f"step{it['step']}")
            n_c = sum(r["correct"] for r in res if r["subject"] == "country")
            n_ce = sum(r["correct"] for r in res if r["subject"] == "city_enc")
            row = {"step": it["step"], "country_correct": n_c, "city_enc_correct": n_ce,
                   "n_refs": 5, "detail": res}
            f.write(json.dumps(row) + "\n"); f.flush()
            print(f"step {it['step']!s:>5}: country {n_c}/5, city {n_ce}/5")
            for r in res:
                mark = "OK " if r["correct"] else "XX "
                print(f"    {mark}[{r['subject']:<8}] {r['ref']} exp={r['expected']!r:<16} got={r['response']!r}")
    print(f"\n-> {out_fp}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sft-out", required=True)
    ap.add_argument("--shim-url", default="http://127.0.0.1:8101/v1")
    ap.add_argument("--base-ckpt", default="Qwen/Qwen3-235B-A22B-Instruct-2507")
    ap.add_argument("--steps", default="0,final", help="'0,final' | 'all' | comma list")
    ap.add_argument("--out", default="runs")
    asyncio.run(_run(ap.parse_args()))


if __name__ == "__main__":
    main()
