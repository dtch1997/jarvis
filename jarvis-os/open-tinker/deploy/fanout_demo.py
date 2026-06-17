"""Burst fan-out demo against the DEPLOYED control plane (#31 burst tuning).

Fires a concurrent burst of ``compute_logprobs`` requests at the real deployed
``/v1/logprobs`` and reports the latency distribution, so you can watch the
sampler tier autoscale and *right-size* ``OPEN_TINKER_MODAL_MIN_SAMPLERS``.

Why not ``modal run …::fanout``: that launched an *ephemeral* Modal app whose
image is rebuilt and (observed) can resolve torch differently from the deployed
image — so it doesn't exercise the tier you actually serve. This drives the
deployed endpoint over real HTTP via the ``open_tinker`` client (the same shim
``parity_probe.py`` uses), so what you measure is what you ship.

Reading the result — right-sizing the warm pool (``OPEN_TINKER_MODAL_MIN_SAMPLERS``):
  * A request served by a warm sampler returns in ~the model's forward time.
  * A request that triggers a cold container pays the full model load (seconds→
    minutes), which shows up as a long p95/max tail and, past the web-endpoint
    timeout, as 408/5xx failures.
  * Raise MIN_SAMPLERS until the tail collapses for your expected burst width
    (concurrency), then stop — warm containers are idle GPU $. A good first guess
    is the steady-state concurrency you expect; MAX_SAMPLERS still absorbs spikes
    above it (at cold-start latency).

Usage (from open-tinker/, after `modal deploy`):
    export OPEN_TINKER_BASE_URL=<control-plane-url>   # printed on deploy
    python deploy/fanout_demo.py --n 32 --concurrency 16
"""

import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import open_tinker

open_tinker.use_as_tinker()

import tinker  # shimmed to open_tinker  # noqa: E402

MODEL = os.environ.get("OPEN_TINKER_BASE_MODEL", "Qwen/Qwen3.6-27B")


def _percentile(sorted_vals, q):
    """Nearest-rank percentile (q in [0,100]); sorted_vals must be non-empty."""
    if not sorted_vals:
        return float("nan")
    k = max(0, min(len(sorted_vals) - 1, int(round((q / 100.0) * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=32, help="total requests to fire")
    ap.add_argument("--concurrency", type=int, default=16, help="in-flight at once (burst width)")
    ap.add_argument("--prompt-len", type=int, default=8, help="prompt token count per request")
    args = ap.parse_args()

    if not os.environ.get("OPEN_TINKER_BASE_URL"):
        raise SystemExit("set OPEN_TINKER_BASE_URL to the deployed control-plane URL first")

    sc = tinker.ServiceClient()
    samp = sc.create_sampling_client(base_model=MODEL)
    prompt = tinker.types.ModelInput.from_ints(list(range(args.prompt_len)))

    def _one(_i: int):
        t0 = time.time()
        try:
            r = samp.compute_logprobs(prompt)
            r = r.result() if hasattr(r, "result") else r
            ok = r is not None and len(r) == args.prompt_len
            return ok, time.time() - t0, None
        except Exception as e:  # noqa: BLE001 — count failures (e.g. cold-start 408s)
            return False, time.time() - t0, type(e).__name__

    print(f"firing {args.n} logprobs requests @ concurrency {args.concurrency} -> {os.environ['OPEN_TINKER_BASE_URL']}")
    wall0 = time.time()
    lats, n_ok, errs = [], 0, {}
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        for ok, lat, err in (f.result() for f in as_completed(ex.submit(_one, i) for i in range(args.n))):
            lats.append(lat)
            n_ok += int(ok)
            if err:
                errs[err] = errs.get(err, 0) + 1
    wall = time.time() - wall0

    lats.sort()
    print(f"  done in {wall:.1f}s — {n_ok}/{args.n} ok, throughput {args.n / wall:.1f} req/s")
    print(f"  latency (s): min {lats[0]:.2f}  p50 {_percentile(lats, 50):.2f}  "
          f"p95 {_percentile(lats, 95):.2f}  max {lats[-1]:.2f}")
    if errs:
        print(f"  failures: {errs}  (cold-start/timeout? raise OPEN_TINKER_MODAL_MIN_SAMPLERS)")
    # A genuine cold-start tail is many seconds (a full model load), not sub-second
    # connection/warm-up jitter — gate on an absolute floor AND a tail well above p50.
    p50 = _percentile(lats, 50)
    if lats[-1] > 5.0 and lats[-1] > 3 * max(p50, 1e-6):
        print("  NOTE: long tail vs p50 — burst spilled onto cold containers; raise the warm "
              "pool (OPEN_TINKER_MODAL_MIN_SAMPLERS) toward --concurrency to flatten p95/max.")


if __name__ == "__main__":
    main()
