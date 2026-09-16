"""On-pod driver: smoke every arm, then run the shuffled config matrix.

Writes runs.jsonl (one line per run: label + start/end timestamps + status)
next to the telemetry file, and prints DRIVER_DONE at the end so the devbox
poll can gate on a log marker.

Usage: python driver.py --out results [--duration 150] [--smoke-only]
"""
import argparse, itertools, json, os, random, subprocess, sys, time

ARMS = ["sft", "pretrain", "dpo", "grpo", "sft_eval", "infer"]
MODELS = ["Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct"]
BATCH = [4, 16]
SEQLEN = 384
IDLE_GAP = 15.0


def run_one(out, arm, model, bs, seqlen, duration, seed, run_id, tag):
    log = os.path.join(out, "logs", f"{run_id}.log")
    os.makedirs(os.path.dirname(log), exist_ok=True)
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "workloads.py"),
           "--arm", arm, "--model", model, "--bs", str(bs), "--seqlen", str(seqlen),
           "--duration", str(duration), "--seed", str(seed), "--run-id", run_id]
    rec = dict(run_id=run_id, tag=tag, arm=arm, model=model, bs=bs, seqlen=seqlen,
               duration=duration, seed=seed, t_launch=time.time())
    with open(log, "w") as lf:
        p = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT)
    rec["t_end"] = time.time()
    rec["exit"] = p.returncode
    # workloads.py prints a JSON status line (t_ready = model loaded, first step
    # time, steps completed); pick it up from the log
    rec["status"] = "ok" if p.returncode == 0 else "failed"
    try:
        for line in open(log):
            if line.startswith("WORKLOAD_STATUS "):
                rec.update(json.loads(line[len("WORKLOAD_STATUS "):]))
    except Exception as e:  # noqa: BLE001
        rec["status_parse_err"] = str(e)
    if p.returncode != 0:
        tail = open(log).read().splitlines()[-15:]
        rec["error_tail"] = "\n".join(tail)
    with open(os.path.join(out, "runs.jsonl"), "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"[driver] {run_id} {arm} {model} bs={bs} -> {rec['status']} "
          f"({rec['t_end'] - rec['t_launch']:.0f}s)", flush=True)
    return rec


def idle(out, seconds, run_id):
    t0 = time.time()
    time.sleep(seconds)
    with open(os.path.join(out, "runs.jsonl"), "a") as f:
        f.write(json.dumps(dict(run_id=run_id, tag="idle", arm="idle", model=None, bs=None,
                                seqlen=None, t_launch=t0, t_ready=t0, t_end=time.time(),
                                status="ok")) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results")
    ap.add_argument("--duration", type=float, default=150.0)
    ap.add_argument("--smoke-duration", type=float, default=20.0)
    ap.add_argument("--smoke-only", action="store_true")
    ap.add_argument("--skip-smoke", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    if not a.skip_smoke:
        print("[driver] smoke pass", flush=True)
        bad = []
        for i, arm in enumerate(ARMS):
            r = run_one(a.out, arm, MODELS[0], 4, SEQLEN, a.smoke_duration, a.seed,
                        f"smoke-{i:02d}-{arm}", "smoke")
            if r["status"] != "ok":
                bad.append(arm)
        if bad:
            print(f"[driver] SMOKE FAILED for arms {bad}; aborting before the matrix", flush=True)
            print("DRIVER_DONE status=smoke_failed", flush=True)
            return 2
        if a.smoke_only:
            print("DRIVER_DONE status=smoke_ok", flush=True)
            return 0

    cells = list(itertools.product(ARMS, MODELS, BATCH))
    rng = random.Random(a.seed)
    rng.shuffle(cells)
    print(f"[driver] matrix: {len(cells)} runs x {a.duration}s", flush=True)
    for i, (arm, model, bs) in enumerate(cells):
        idle(a.out, IDLE_GAP, f"idle-{i:02d}")
        run_one(a.out, arm, model, bs, SEQLEN, a.duration, a.seed + i, f"run-{i:02d}-{arm}", "matrix")
    idle(a.out, IDLE_GAP, "idle-end")
    print("DRIVER_DONE status=ok", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
