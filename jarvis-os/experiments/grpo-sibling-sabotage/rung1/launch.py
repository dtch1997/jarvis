"""Launch the Rung 1 job on an ephemeral RunPod A100 via bellhop.

Pushes this directory, installs the pinned requirements, runs run_all.sh,
pulls results/ back to rung1/results/.
"""

import asyncio
import pathlib

from bellhop import PodConfig, RunSpec, run

HERE = pathlib.Path(__file__).parent


async def main():
    res = await run(
        RunSpec(
            slug="grpo-spite-rung1",
            codebase=str(HERE),
            setup="pip uninstall -y -q torchvision torchaudio; pip install -q -r requirements.lock",
            run="bash run_all.sh",
            results_subdir="results",
        ),
        PodConfig(gpu="A100", container_disk_gb=60),
    )
    print("exit:", res.remote_exit)
    print("results:", res.local_results)


if __name__ == "__main__":
    asyncio.run(main())
