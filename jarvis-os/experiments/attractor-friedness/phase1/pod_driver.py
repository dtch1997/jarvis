"""On-pod orchestrator for one suite (env SUITE in {em, ab, oct}).

cwd = bellhop run_dir (/workspace/<slug>). v2: LoRA adapters are MERGED into
full weights and every model gets its own vLLM boot — LoRA-serving +
prompt_logprobs crashed vLLM's engine on the Llama suite in v1, and a dead
engine silently poisoned every later benchmark. Merged dirs are deleted
after their eval to fit the disk. Outcomes record per-benchmark status
parsed from summary.json, not just CLI exit codes.
"""

import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

JOB = pathlib.Path.cwd()
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
    paths = {}
    for name, (repo, sub) in suite["adapters"].items():
        dest = JOB / "adapters" / name
        if not dest.exists():
            log(f"downloading {repo}" + (f"/{sub}" if sub else ""))
            snapshot_download(repo_id=repo, local_dir=str(dest),
                              allow_patterns=[f"{sub}/*"] if sub else None)
        paths[name] = dest / sub if sub else dest
    return paths


def nothink_template():
    from transformers import AutoTokenizer
    tmpl = AutoTokenizer.from_pretrained(BASE).chat_template
    needle = "enable_thinking is defined and enable_thinking is false"
    if needle not in tmpl:
        log("WARNING: nothink needle not found; serving stock template")
        return None
    f = JOB / "nothink.jinja"
    f.write_text(tmpl.replace(
        needle, "not (enable_thinking is defined and enable_thinking is true)"))
    return f


def boot_vllm(model_path, served_name, chat_template):
    cmd = (f"{FMO}/.venv-vllm/bin/vllm serve '{model_path}' --port {PORT} "
           f"--served-model-name '{served_name}' "
           f"--gpu-memory-utilization 0.90 --max-model-len 8192 --disable-log-requests")
    if chat_template:
        cmd += f" --chat-template {chat_template}"
    if not port_free():
        raise RuntimeError("port 8000 still occupied before boot — previous vllm not dead")
    logf = (RESULTS / f"vllm-{served_name.replace('/', '_')}.log").open("w")
    log(f"booting vllm: {cmd}")
    proc = subprocess.Popen(cmd, shell=True, stdout=logf, stderr=subprocess.STDOUT,
                            start_new_session=True)
    deadline = time.time() + 45 * 60
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"vllm exited early rc={proc.returncode}")
        try:
            with urllib.request.urlopen(f"{BASE_URL}/models", timeout=5) as r:
                if r.status == 200:
                    probe_model(served_name)
                    log(f"vllm ready and answering for '{served_name}'")
                    return proc
        except RuntimeError:
            raise
        except Exception:
            pass
        time.sleep(10)
    raise RuntimeError("vllm not ready after 45min")


def port_free():
    try:
        urllib.request.urlopen(f"{BASE_URL}/models", timeout=3)
        return False
    except urllib.error.URLError:
        return True
    except Exception:
        return False


def probe_model(name):
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions", method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"model": name, "max_tokens": 5,
                         "messages": [{"role": "user", "content": "hi"}]}).encode())
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            if r.status != 200:
                raise RuntimeError(f"probe for '{name}' -> HTTP {r.status}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"probe for '{name}' -> HTTP {e.code}: {e.read()[:200]}")


def kill_vllm(proc):
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=120)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=30)
    deadline = time.time() + 300
    while time.time() < deadline:
        if port_free():
            time.sleep(5)
            return
        time.sleep(5)
    raise RuntimeError("port 8000 never freed after kill")


def summary_status(name):
    f = FMO / "runs" / "eval" / name / "summary.json"
    if not f.exists():
        return {"summary": "MISSING"}
    b = json.loads(f.read_text()).get("benchmarks", {})
    return {k: ("ERR" if isinstance(v, dict) and "error" in v else "ok") for k, v in b.items()}


def eval_model(name):
    t0 = time.time()
    ok = {}
    bat = RESULTS / "battery" / (name.replace("/", "_") + ".jsonl")
    r = sh(f"{FMO}/.venv/bin/python {JOB}/phase1/pod_battery.py "
           f"--base-url {BASE_URL} --model '{name}' --out {bat}")
    nerr = sum(1 for l in bat.read_text().splitlines() if '"error"' in l) if bat.exists() else -1
    ok["battery"] = "ok" if r.returncode == 0 and nerr == 0 else f"ERR({nerr})"
    r = sh(f"cd {FMO} && .venv/bin/mu-decisiveness --backend openai --mode logprob "
           f"--model-id '{name}' --base-url {BASE_URL} --name '{name.replace('/', '_')}'")
    ok["mu"] = "ok" if r.returncode == 0 else "ERR"
    sh(f"cd {FMO} && .venv/bin/evalsuite --endpoint {BASE_URL} "
       f"--model '{name}' --tokenizer '{BASE}' --name '{name.replace('/', '_')}' "
       f"--benchmarks mmlu,ifeval,perplexity,safety,sentiment")
    ok.update(summary_status(name.replace("/", "_")))
    log(f"model {name} done in {(time.time()-t0)/60:.1f}min: {ok}")
    return ok


def main():
    log(f"suite={SUITE} base={BASE} (v2 merged serving)")
    (RESULTS / "battery").mkdir(exist_ok=True)
    adapter_paths = download_adapters()
    tmpl = nothink_template() if suite["nothink"] else None
    outcomes = {}

    proc = boot_vllm(BASE, BASE, tmpl)
    try:
        outcomes[BASE] = eval_model(BASE)
    finally:
        kill_vllm(proc)

    for name, apath in adapter_paths.items():
        merged = JOB / "merged" / name
        try:
            if not merged.exists():
                r = sh(f"{FMO}/.venv/bin/python {JOB}/phase1/merge_lora.py "
                       f"--base '{BASE}' --adapter '{apath}' --out '{merged}'")
                if r.returncode != 0:
                    outcomes[name] = {"merge": "ERR"}
                    continue
            proc = boot_vllm(merged, name, tmpl)
            try:
                outcomes[name] = eval_model(name)
            finally:
                kill_vllm(proc)
        except Exception as e:
            outcomes[name] = {"fatal": f"{type(e).__name__}: {e}"}
            log(f"model {name} FATAL: {e}")
        finally:
            shutil.rmtree(merged, ignore_errors=True)
        (RESULTS / "outcomes.json").write_text(json.dumps(outcomes, indent=2))

    for d in ("eval", "elicit"):
        src = FMO / "runs" / d
        if src.exists():
            shutil.copytree(src, RESULTS / d, dirs_exist_ok=True)
    (RESULTS / "outcomes.json").write_text(json.dumps(outcomes, indent=2))
    log(f"suite {SUITE} complete: {json.dumps(outcomes)}")
    bad = [n for n, ok in outcomes.items()
           if any(v not in ("ok",) for v in ok.values())]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
