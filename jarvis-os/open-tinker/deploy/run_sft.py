"""Launch battery-sft against the open-tinker backend.

Calls ``open_tinker.use_as_tinker()`` BEFORE the cookbook imports, then delegates
to battery's real CLI (``battery.train.tinker.sft.main``) — so battery runs
completely unchanged, only the tinker backend is swapped.

    OPEN_TINKER_BASE_URL=https://<pod>.proxy.runpod.net \
      python deploy/run_sft.py --data conversations.jsonl --model ... [--smoke]
"""

import sys

import open_tinker

open_tinker.use_as_tinker()

from battery.train.tinker import sft  # noqa: E402  (after the shim)

if __name__ == "__main__":
    sft.main(sys.argv[1:])
