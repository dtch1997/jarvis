"""Local driver: provision an A100 pod, train the paired organism, push to HF.

Reads creds from ~/.env (RUNPOD_API_KEY, HF_TOKEN). Streams pod logs to stdout;
pulls selfchecks + built data back locally. Set SMOKE=1 for a tiny end-to-end
validation before the full run.

  SMOKE=1 python drive_bellhop.py        # ~6 steps, tiny data, HF push to *-smoke
  python drive_bellhop.py                # full run
"""
from __future__ import annotations
import asyncio, os
from datetime import timedelta
from pathlib import Path

from bellhop import pod, PodConfig

HERE = Path(__file__).resolve().parent
SMOKE = os.environ.get("SMOKE", "0") == "1"
DATA_SEED = os.environ.get("ARCH_DATA_SEED", "20260703")


def load_env(path=os.path.expanduser("~/.env")):
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


async def main():
    load_env()
    assert os.environ.get("RUNPOD_API_KEY"), "RUNPOD_API_KEY missing"
    assert os.environ.get("HF_TOKEN"), "HF_TOKEN missing"

    cfg = PodConfig(
        gpu="A100", gpu_count=1,
        image_preset="pytorch-cuda",
        container_disk_gb=150,
        cloud="SECURE", cloud_fallback=True,
        name="hidden-effect-organism",
        max_lifetime=timedelta(hours=4),
        stop_after=timedelta(hours=4),
    )
    pod_env = {
        "ARCH_DATA_SEED": DATA_SEED,
        "HF_TOKEN": os.environ["HF_TOKEN"],
        "SMOKE": "1" if SMOKE else "0",
    }

    async with pod(cfg) as p:
        print(f"[drive] pod up; pushing code (SMOKE={SMOKE})", flush=True)
        await p.push(str(HERE), "/workspace/job")
        print("[drive] running organism pipeline on pod ...", flush=True)
        r = await p.exec("cd /workspace/job && bash run_on_pod.sh 2>&1",
                         env=pod_env, timeout=3.5 * 3600)
        print(r.stdout[-8000:])
        if r.exit_code != 0:
            print(f"[drive] POD RUN FAILED rc={r.exit_code}\nSTDERR:\n{r.stderr[-4000:]}", flush=True)
            raise SystemExit(r.exit_code)
        # pull back small artifacts (selfchecks + built data), not the big trajectories
        out_local = HERE / ("pulled_smoke" if SMOKE else "pulled")
        await p.exec("cd /workspace/job && mkdir -p _pull && cp runs/M/selfcheck.json _pull/selfcheck_M.json "
                     "&& cp runs/U/selfcheck.json _pull/selfcheck_U.json && cp -r data _pull/data", timeout=120)
        await p.pull("/workspace/job/_pull", str(out_local))
        print(f"[drive] pulled selfchecks + data -> {out_local}", flush=True)
    print("[drive] DONE — pod torn down", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
