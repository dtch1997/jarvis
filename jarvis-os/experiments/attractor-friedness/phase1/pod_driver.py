"""On-pod orchestrator for one suite (env SUITE in {em, ab, oct}).

Layout on the pod (cwd = bellhop run_dir = the pushed experiment dir):
  fmo/            fried-model-organisms clone (setup step; .venv synced, .venv-vllm built)
  results/        pulled back by bellhop (battery/, eval/, elicit/, logs)

Per suite: download LoRA adapters -> boot one vLLM with --lora-modules ->
for base + each adapter: fingerprint battery, mu-decisiveness, evalsuite.
Per-model failures are recorded and skipped, never fatal.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import urllib.request

JOB = pathlib.Path.cwd()  # bellhop run_dir = /workspace/<slug>
FMO = JOB / "fmo"
RESULTS = JOB / "results"
PORT = 8000
BASE_URL = f"http://localhost:{PORT}/v1"

sys.path.insert(0, str(JOB / "phase1"))
from panel import SUITES

SUITE = os.environ["SUITE"]
suite = SUITES[SUITE]
BASE = suite["base"]
RESULTS.mkdir(exist_ok=True)
STATUS = RESULTS / "status.jsonl"


def log(msg):
    print(f"[driver {time.strftime('%H:%M:%S')}] {msg}", flush=True)
    with STATUS.open("a") as f:
        f.write(json.dumps({"t": time.time(), "msg": msg}) + "\n")


def sh(cmd, **kw):
    log(f"$ {cmd}")
    return subprocess.run(cmd, shell=True, **kw)


def download_adapters():
    from huggingface_hub import snapshot_download
    paths, ranks = {}, []
    for name, (repo, sub) in suite["adapters"].items():
        dest = JOB / "adapters" / name
        if not dest.exists():
            log(f"downloading {repo}" + (f"/{sub}" if sub else ""))
            snapshot_download(repo_id=repo, local_dir=str(dest),
                              allow_patterns=[f"{sub}/*"] if sub else None)
        path = dest / sub if sub else dest
        cfg = json.loads((path / "adapter_config.json").read_text())
        ranks.append(int(cfg.get("r", 16)))
        paths[name] = path
    return paths, max(ranks)


def nothink_template():
    """Qwen3: flip the chat template so thinking is OFF unless asked for."""
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(BASE)
    tmpl = tok.chat_template
    needle = "enable_thinking is defined and enable_thinking is false"
    if needle not in tmpl:
        log("WARNING: nothink needle not found; serving stock template")
        return None
    patched = tmpl.replace(needle, "not (enable_thinking is defined and enable_thinking is true)")
    f = JOB / "nothink.jinja"
    f.write_text(patched)
    return f


def boot_vllm(adapter_paths, max_rank, chat_template):
    rank = 8
    while rank < max_rank:
        rank *= 2
    mods = " ".join(f"{n}={p}" for n, p in adapter_paths.items())
    cmd = (f"{FMO}/.venv-vllm/bin/vllm serve {BASE} --port {PORT} "
           f"--enable-lora --lora-modules {mods} --max-lora-rank {rank} "
           f"--max-loras 2 --max-cpu-loras {len(adapter_paths)} "
           f"--gpu-memory-utilization 0.90 --max-model-len 8192 --disable-log-requests")
    if chat_template:
        cmd += f" --chat-template {chat_template}"
    logf = (RESULTS / f"vllm-{SUITE}.log").open("w")
    log(f"booting vllm: {cmd}")
    proc = subprocess.Popen(cmd, shell=True, stdout=logf, stderr=subprocess.STDOUT)
    deadline = time.time() + 45 * 60
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"vllm exited early rc={proc.returncode}; see vllm-{SUITE}.log")
        try:
            with urllib.request.urlopen(f"{BASE_URL}/models", timeout=5) as r:
                if r.status == 200:
                    log("vllm ready")
                    return proc
        except Exception:
            pass
        time.sleep(10)
    raise RuntimeError("vllm not ready after 45min")


def eval_model(name):
    t0 = time.time()
    ok = {"battery": False, "mu": False, "evalsuite": False}

    r = sh(f"{FMO}/.venv/bin/python {JOB}/phase1/pod_battery.py "
           f"--base-url {BASE_URL} --model '{name}' --out {RESULTS}/battery/{name}.jsonl")
    ok["battery"] = r.returncode == 0

    r = sh(f"cd {FMO} && .venv/bin/mu-decisiveness --backend openai --mode logprob "
           f"--model-id '{name}' --base-url {BASE_URL} --name '{name}'")
    ok["mu"] = r.returncode == 0

    r = sh(f"cd {FMO} && .venv/bin/evalsuite --endpoint {BASE_URL} "
           f"--model '{name}' --tokenizer '{BASE}' --name '{name}' "
           f"--benchmarks mmlu,ifeval,perplexity,safety,sentiment")
    ok["evalsuite"] = r.returncode == 0

    log(f"model {name} done in {(time.time()-t0)/60:.1f}min: {ok}")
    return ok


def main():
    log(f"suite={SUITE} base={BASE}")
    (RESULTS / "battery").mkdir(exist_ok=True)
    adapter_paths, max_rank = download_adapters()
    tmpl = nothink_template() if suite["nothink"] else None
    proc = boot_vllm(adapter_paths, max_rank, tmpl)
    outcomes = {}
    try:
        for name in [BASE] + list(adapter_paths):
            outcomes[name] = eval_model(name)
    finally:
        proc.terminate()
    for d in ("eval", "elicit"):
        src = FMO / "runs" / d
        if src.exists():
            shutil.copytree(src, RESULTS / d, dirs_exist_ok=True)
    (RESULTS / "outcomes.json").write_text(json.dumps(outcomes, indent=2))
    log(f"suite {SUITE} complete: {outcomes}")
    failures = [n for n, ok in outcomes.items() if not all(ok.values())]
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
