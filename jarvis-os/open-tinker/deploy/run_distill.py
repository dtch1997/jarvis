"""Launch battery-distill (on-policy reverse-KL) against the open-tinker backend.

Mirrors run_sft.py: calls ``open_tinker.use_as_tinker()`` BEFORE the cookbook
imports, then delegates to battery's real CLI (``battery.train.tinker.distill.main``),
so battery + tinker_cookbook run unchanged against our backend.

    OPEN_TINKER_BASE_URL=http://localhost:18200 \
      python deploy/run_distill.py --model ... --teacher-model ... --sys "..." \
      --prompts prompts.jsonl --smoke
"""

import sys

import open_tinker

open_tinker.use_as_tinker()

from battery.train.tinker import distill  # noqa: E402  (after the shim)

if __name__ == "__main__":
    distill.main(sys.argv[1:])
