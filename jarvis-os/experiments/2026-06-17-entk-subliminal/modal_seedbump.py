"""Run the ARC-17 seed-bumps (phase8, phase10) on parallel Modal CPU containers.

    modal run modal_seedbump.py

Each phase runs in its own 8-CPU container; the resulting results/<phase>.json is returned
and written back into the local results/ dir. Figures are made locally afterwards.
"""
import os
import modal

EXP = os.path.dirname(os.path.abspath(__file__))

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("numpy")
    .pip_install("torch", index_url="https://download.pytorch.org/whl/cpu")
    .add_local_dir(EXP, remote_path="/root/exp",
                   ignore=["mnist", "results", "__pycache__", "*.png", "*.log", "*.json", "*.md"])
)
app = modal.App("arc17-seedbump")


@app.function(image=image, cpu=8.0, timeout=3600)
def run_phase(script: str, json_name: str, seeds: int):
    import subprocess
    os.chdir("/root/exp")
    os.makedirs("results", exist_ok=True)
    r = subprocess.run(["python", "-u", script, "--seeds", str(seeds)],
                       capture_output=True, text=True)
    jpath = f"results/{json_name}"
    content = open(jpath).read() if os.path.exists(jpath) else None
    tail = (r.stdout + "\n" + r.stderr)[-2500:]
    return {"json_name": json_name, "content": content, "rc": r.returncode, "tail": tail}


@app.local_entrypoint()
def main():
    jobs = [("phase8_structured.py", "phase8.json"), ("phase10_permutation.py", "phase10.json")]
    handles = [run_phase.spawn(s, j, 6) for s, j in jobs]
    for h in handles:
        res = h.get()
        print(f"\n===== {res['json_name']} (rc={res['rc']}) =====")
        print(res["tail"])
        if res["content"]:
            with open(os.path.join(EXP, "results", res["json_name"]), "w") as f:
                f.write(res["content"])
            print(f"[wrote results/{res['json_name']}]")
        else:
            print("[no json produced — see tail above]")
