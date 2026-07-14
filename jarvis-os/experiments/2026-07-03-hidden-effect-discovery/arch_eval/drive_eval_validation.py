"""Local driver: validate the eval harness against the REAL organism on a pod.

Pushes arch_eval/ + held-out probes, downloads the organism from HF, scores the
control + perplexity_diff example submissions, pulls the result JSONs back.

Reads creds from ~/.env (RUNPOD_API_KEY, HF_TOKEN, ANTHROPIC_API_KEY).
"""
from __future__ import annotations
import asyncio, os
from datetime import timedelta
from pathlib import Path

from bellhop import pod, PodConfig

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "organism" / "pulled" / "_pull" / "data"   # built probes


def load_env(path=os.path.expanduser("~/.env")):
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


async def main():
    load_env()
    for k in ("RUNPOD_API_KEY", "HF_TOKEN", "ANTHROPIC_API_KEY"):
        assert os.environ.get(k), f"{k} missing"

    cfg = PodConfig(gpu="A100", gpu_count=1, image_preset="pytorch-cuda",
                    container_disk_gb=100, cloud="SECURE", cloud_fallback=True,
                    name="hidden-effect-eval-validation",
                    max_lifetime=timedelta(hours=2), stop_after=timedelta(hours=2))
    pod_env = {"HF_TOKEN": os.environ["HF_TOKEN"],
               "ANTHROPIC_API_KEY": os.environ["ANTHROPIC_API_KEY"]}

    async with pod(cfg) as p:
        print("[drive] pod up; pushing eval + data", flush=True)
        await p.push(str(HERE), "/workspace/job")
        await p.push(str(DATA), "/workspace/job/data")
        print("[drive] running eval validation ...", flush=True)
        r = await p.exec("cd /workspace/job && bash run_eval_validation.sh 2>&1",
                         env=pod_env, timeout=1.5 * 3600)
        print(r.stdout[-12000:])
        if r.exit_code != 0:
            print(f"[drive] FAILED rc={r.exit_code}\n{r.stderr[-3000:]}", flush=True)
        await p.exec("cd /workspace/job && mkdir -p _pull && cp out_*.json _pull/ 2>/dev/null || true", timeout=60)
        await p.pull("/workspace/job/_pull", str(HERE / "eval_validation_out"))
    print("[drive] DONE — pod torn down", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
