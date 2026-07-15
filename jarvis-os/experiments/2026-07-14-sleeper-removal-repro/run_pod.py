"""Driver: run removal_repro.py on an ephemeral RunPod GPU via bellhop.

The job is detached on the pod (nohup > run.log) and polled via short execs,
so progress is visible and a hang is diagnosable from the partial log.
"""

from __future__ import annotations

import asyncio
import os
from datetime import timedelta
from pathlib import Path

from bellhop import PodConfig, pod

HERE = Path(__file__).parent
# The organism was saved by a transformers-5.x era env (the sprint's setup
# installs --upgrade "transformers>=4.44"); match it, on the torch-2.8 image.
PINS = "transformers==5.13.1 peft==0.19.1 accelerate==1.14.0 safetensors huggingface_hub protobuf sentencepiece"
POLL_SECONDS = 30
MAX_POLLS = 90  # 45 min


async def main():
    cfg = PodConfig(
        gpu="A100",
        image="runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404",
        max_lifetime=timedelta(hours=2),
        name="sleeper-repro",
        container_disk_gb=40,
        cloud="SECURE",  # COMMUNITY A100 hosts kept landing without a public port 22
        provision_timeout=timedelta(seconds=900),
    )
    async with pod(cfg) as p:
        print(f"pod id: {p.id}", flush=True)
        await p.push(str(HERE / "pod_job"), "/workspace/job")

        r = await p.exec(
            "nvidia-smi -L && python3 -c 'import torch; print(\"cuda:\", torch.cuda.is_available())'",
            timeout=120,
        )
        print("gpu check:", r.exit_code, r.stdout.strip(), r.stderr[-200:], flush=True)

        r = await p.exec(f"pip install -q --break-system-packages {PINS}", timeout=900)
        print("pip:", r.exit_code, (r.stderr or r.stdout)[-300:], flush=True)
        if r.exit_code != 0:
            raise RuntimeError("pip install failed on pod")

        r = await p.exec(
            "cd /workspace/job && "
            f"(HF_TOKEN={os.environ['HF_TOKEN']} nohup python3 -u removal_repro.py "
            "> run.log 2>&1 &) && echo launched",
            timeout=60,
        )
        print("launch:", r.exit_code, r.stdout.strip(), flush=True)

        done = False
        for i in range(MAX_POLLS):
            await asyncio.sleep(POLL_SECONDS)
            r = await p.exec(
                "tail -c 800 /workspace/job/run.log; "
                "test -f /workspace/job/results.json && echo __DONE__; "
                "pgrep -f removal_repro.py >/dev/null || echo __DEAD__",
                timeout=60,
            )
            print(f"--- poll {i} ---\n{r.stdout[-900:]}", flush=True)
            if "__DONE__" in r.stdout:
                done = True
                break
            if "__DEAD__" in r.stdout and "__DONE__" not in r.stdout:
                print("job process exited without results.json — full log tail:", flush=True)
                r = await p.exec("tail -c 4000 /workspace/job/run.log", timeout=60)
                print(r.stdout, flush=True)
                raise RuntimeError("pod job died")

        if not done:
            raise RuntimeError("pod job did not finish within poll budget")

        await p.pull("/workspace/job/results.json", str(HERE / "removal_repro_results.json"))
    print("done, pod torn down", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
