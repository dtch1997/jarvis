"""Devbox launcher: three bellhop pods, one per suite, in parallel.

    set -a; . ~/.env; set +a
    python jarvis-os/experiments/attractor-friedness/phase1/launch.py
"""

import asyncio
import os
import pathlib
import sys

from bellhop import PodConfig, RunSpec, run

EXP = pathlib.Path(__file__).resolve().parent.parent

SETUP = """
export PATH=$HOME/.local/bin:$PATH
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH=$HOME/.local/bin:$PATH
[ -d fmo ] || git clone --depth 1 https://github.com/ArcadiaImpact/fried-model-organisms fmo
(
  cd fmo
  uv sync --extra api --extra evalsuite
  [ -x .venv-vllm/bin/vllm ] || {
    uv venv .venv-vllm --python 3.11
    uv pip install --python .venv-vllm/bin/python --torch-backend=cu128 vllm==0.11.0
    uv pip install --python .venv-vllm/bin/python 'transformers<5'
    uv pip uninstall --python .venv-vllm/bin/python flashinfer-python flashinfer-cubin || true
    rm -rf .venv-vllm/lib/python*/site-packages/flashinfer || true
  }
)
"""


async def main():
    suites = sys.argv[1:] or ["em", "ab", "oct"]
    env = {k: os.environ[k] for k in ("HF_TOKEN", "OPENAI_API_KEY") if k in os.environ}
    jobs = []
    for s in suites:
        spec = RunSpec(
            slug=f"attractor-friedness-p1-{s}",
            codebase=str(EXP),
            setup=SETUP,
            run="./fmo/.venv/bin/python phase1/pod_driver.py",
            results_subdir="results",
            env={**env, "SUITE": s},
            timeout=11 * 3600,
        )
        cfg = PodConfig(gpu="H100", container_disk_gb=200,
                        cuda_versions=["12.8", "12.9", "13.0", "13.1"],
                        env={**env, "SUITE": s})
        jobs.append(run(spec, cfg))
    results = await asyncio.gather(*jobs, return_exceptions=True)
    for s, r in zip(suites, results):
        if isinstance(r, Exception):
            print(f"{s}: FAILED {type(r).__name__}: {r}")
        else:
            print(f"{s}: exit={r.remote_exit} results={r.local_results} gcs={r.gcs_uri}")
            print(f"   log tail: {r.log_tail[-500:] if r.log_tail else ''}")


if __name__ == "__main__":
    asyncio.run(main())
