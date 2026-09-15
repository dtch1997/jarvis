"""Phase 0 driver (devbox): one H100 pod via bellhop, on-pod driver polled through a
stagehand flow, results pulled to ./results, then analyze.py.

    python launch.py [--duration 150] [--smoke-only] [--skip-analysis]

Pod id is printed the moment the pod exists and written to results/pod.json so
the pod-digest can attribute spend. Teardown = bellhop scope exit; backstops =
max_lifetime 4 h (native TTL) + an on-pod `sleep 4h && terminate` watchdog.
"""
import argparse, asyncio, json, os, subprocess, sys, time
from datetime import timedelta
from pathlib import Path

import contextlib
from bellhop import PodConfig, pod
from bellhop.pod import Pod
from bellhop.rest import RunpodRest
from stagehand import Flow, live_dashboard, monitor, serve

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
IMAGE = "runpod/pytorch:1.3.0-cu1290-torch291-ubuntu2404"   # torch 2.9.1 preinstalled
REMOTE = "/workspace/gwf"


def load_env():
    for line in open(os.path.expanduser("~/.env")):
        if "=" in line and not line.startswith("#"):
            k, v = line.rstrip("\n").split("=", 1)
            os.environ.setdefault(k, v.strip().strip('"'))


@contextlib.asynccontextmanager
async def adopt(pod_id: str, pc: PodConfig):
    """Attach to an already-running pod (e.g. orphaned by a killed launcher); same teardown-on-exit."""
    async with RunpodRest(api_key=os.environ["RUNPOD_API_KEY"]) as rest:
        p = Pod(rest, pod_id, pc)
        try:
            await p._wait_provision()
            await p._wait_ready()
            yield p
        finally:
            with contextlib.suppress(Exception):
                await p.teardown()


async def run_on_pod(opts: dict) -> dict:
    key = os.environ["RUNPOD_API_KEY"]
    pc = PodConfig(
        gpu="H100", cloud="SECURE", image=IMAGE, container_disk_gb=60,
        name="gpu-workload-fingerprint-p0", max_lifetime=timedelta(hours=4),
        provision_timeout=timedelta(minutes=20), ready_timeout=timedelta(minutes=10),  # big image pull: 300 s default was not enough
        env={"RUNPOD_API_KEY": key},
    )
    RESULTS.mkdir(exist_ok=True)
    ctx = adopt(opts["adopt"], pc) if opts.get("adopt") else pod(pc)
    async with ctx as p:
        info = {"pod_id": p.id, "name": pc.name, "t_create": time.time(), "image": IMAGE}
        print(f"POD {p.id} name={pc.name}", flush=True)
        (RESULTS / "pod.json").write_text(json.dumps(info))
        await p.push(HERE / "pod", REMOTE)
        # NB: every `nohup … &` sits on its own line — `a && nohup b &` would
        # background the whole list as a subshell that keeps the ssh pipe open.
        r = await p.exec(
            f"cd {REMOTE}\n"
            f"python -m pip install -q --break-system-packages -r requirements.in || python -m pip install -q -r requirements.in\n"
            f"nvidia-smi --query-gpu=name,driver_version --format=csv,noheader\n"
            f"python -c 'import torch,trl,transformers;print(torch.__version__,trl.__version__,transformers.__version__)'\n")
        print("[setup]", r.stdout.strip(), r.stderr.strip()[-300:], flush=True)
        if r.exit_code != 0:
            raise RuntimeError(f"setup failed: {r.stderr[-800:]}")
        info["gpu"] = r.stdout.strip().splitlines()[0]
        (RESULTS / "pod.json").write_text(json.dumps(info))
        # pod-side watchdog: terminate self after 4h no matter what the devbox does (idempotent)
        await p.exec(f"if ! pgrep -f watchdog.sh >/dev/null; then nohup bash {REMOTE}/watchdog.sh 14400 > /workspace/watchdog.log 2>&1 < /dev/null & fi\n")
        await p.exec(f"mkdir -p {REMOTE}/results\ncd {REMOTE}\n"
                     f"nohup python telemetry.py --hz 10 --out results/telemetry.jsonl --stop-file results/telemetry.stop "
                     f"> results/telemetry.log 2>&1 < /dev/null &\n")
        flags = "--smoke-only" if opts["smoke_only"] else ""
        await p.exec(f"cd {REMOTE}\nnohup python driver.py --out results --duration {opts['duration']} {flags} "
                     f"> results/driver.log 2>&1 < /dev/null &\n")

        n_runs = 6 if opts["smoke_only"] else 6 + 24
        with monitor("pod-runs", total=n_runs) as m:
            done, status = 0, None
            while status is None:
                await asyncio.sleep(30)
                r = await p.exec(f"cd {REMOTE}/results && (grep -c '\"tag\": \"[sm]' runs.jsonl 2>/dev/null || echo 0); "
                                 f"tail -n 1 driver.log; grep -o 'DRIVER_DONE.*' driver.log || true")
                lines = r.stdout.strip().splitlines()
                try:
                    now = int(lines[0])
                except (IndexError, ValueError):
                    now = done
                if now > done:
                    m.update(n=now - done, last=lines[1] if len(lines) > 1 else "")
                    done = now
                else:
                    m.set(last=lines[1] if len(lines) > 1 else "")
                for l in lines:
                    if l.startswith("DRIVER_DONE"):
                        status = l.split("status=")[-1]
        print(f"[driver] finished status={status}", flush=True)
        await p.exec(f"touch {REMOTE}/results/telemetry.stop; sleep 3; rm -rf /tmp/wl-out")
        await p.pull(f"{REMOTE}/results", str(RESULTS))
        nested = RESULTS / "results"  # pull of a dir lands as results/results/ — flatten
        if nested.is_dir():
            for f in nested.iterdir():
                f.rename(RESULTS / f.name)
            nested.rmdir()
        info.update(t_end=time.time(), driver_status=status)
        (RESULTS / "pod.json").write_text(json.dumps(info))
    return info


async def analyze(info: dict) -> dict:
    if info.get("skip_analysis"):
        return {}
    py = os.environ.get("GWF_ANALYSIS_PYTHON", sys.executable)
    r = subprocess.run([py, str(HERE / "analyze.py")], capture_output=True, text=True)
    print(r.stdout[-3000:], r.stderr[-2000:], flush=True)
    if r.returncode != 0:
        raise RuntimeError("analyze.py failed")
    return json.loads((RESULTS / "analysis" / "metrics.json").read_text())


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=150.0)
    ap.add_argument("--smoke-only", action="store_true")
    ap.add_argument("--skip-analysis", action="store_true")
    ap.add_argument("--adopt", default=None, help="existing pod id to attach to instead of creating one")
    a = ap.parse_args()
    load_env()
    flow = Flow(str(HERE / "runs"), concurrency=2)
    pod_h = flow.spawn(run_on_pod, args=({"duration": a.duration, "smoke_only": a.smoke_only, "adopt": a.adopt},), name="run-on-pod")
    an_h = flow.spawn(analyze, args=(pod_h,), name="analyze") if not a.skip_analysis else None
    url, stop = None, None
    try:
        url, stop = serve(HERE / "runs", name="gpu-workload-fingerprint", title="gpu-workload-fingerprint p0")
        print(f"DASHBOARD {url}", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"[serve] no lobby: {e}", flush=True)
    async with live_dashboard(flow.runs_dir, title="gpu-workload-fingerprint p0"):
        state = await flow.run()
    print(f"FLOW done={state.done} failed={state.failed}", flush=True)
    if an_h is not None and an_h.result:
        print(json.dumps(an_h.result, indent=1)[:2000])
    if stop:
        stop()
    return 0 if state.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
