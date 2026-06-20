#!/usr/bin/env python3
"""modal-runner driver: fan a configurable script out across many parallel
Modal containers (one per config), collect each container's artifacts back to
the devbox, upload them to GCS, and print a retrieval recipe.

Where runpod-runner provisions a single ephemeral pod, this driver leans on
Modal's native fan-out: it builds one image from the supplied codebase, defines
one function that runs `<script> <config.args>`, and `.map()`s it over the whole
config enumeration with `return_exceptions=True` so a single bad config never
sinks the sweep — the configs that succeeded are still pulled back and uploaded.

It is meant to be launched as ONE background job so it emits exactly one
completion notification (see project CLAUDE.md): no detaching, no `&`.

    python3 run.py --spec /path/to/spec.json

CONTAINER-SAFE IMPORT: Modal re-imports this module *inside every container* to
locate the function, re-running all top-level code. So the driver-only work
(argv parse, spec-file read, filesystem validation, the fan-out, the GCS upload)
is fenced behind `modal.is_local()` / `__main__`. The spec the container needs
is baked into the image as the `MODAL_RUNNER_SPEC` env var (secrets stripped),
so the in-container re-import reconstructs the same globals without touching the
devbox filesystem.

Artifacts travel back through Modal's result channel as an in-memory tar per
config (capped by `max_artifact_mb`), so GCS credentials never leave the devbox
— the upload happens here, locally, after the fan-out completes. For artifacts
too large for that channel (model weights, datasets), have the script upload
them itself from inside the container via a Modal Volume / GCS secret instead.

Spec schema (JSON object):
    REQUIRED
      slug            short kebab-case id; names the local dir + GCS path + app
      codebase        absolute path to a local dir; shipped via add_local_dir
      script          path to the script to run, RELATIVE to the codebase root
      configs         list of config objects, ONE CONTAINER EACH:
                        {"id": "lr0.1_s0",            # unique; names the artifact dir
                         "args": ["--lr","0.1"],      # appended to: python -u <script>
                         "env": {"SEED":"0"}}         # optional, non-secret, per-config
    IMAGE / DEPS (optional)
      image_preset    name from ../standard-images.json (e.g. "cpu-base",
                      "pytorch-cuda", "vllm"); default "cpu-base"
      image           free-form docker registry tag; overrides image_preset and
                      starts the build from that image (Modal from_registry)
      add_python      python to add onto a from_registry/free-form image; set
                      null to use the image's own python (default: python_version)
      python_version  python for the debian_slim base (cpu-base); default "3.11"
      pip_install     list of packages (layered on top of whichever base)
      pip_install_torch_cpu  bool; adds torch from the CPU wheel index
      apt_install     list of apt packages
      requirements_txt  path (relative to codebase) to a requirements file
      uv_sync         bool; `uv sync` the codebase (needs pyproject + uv.lock)
    COMPUTE (optional)
      gpu             e.g. "A10G", "A100", "A100-80GB", "H100", "T4:2"; null = CPU
      cpu             float cores (default 4.0)
      memory_mb       int MB (default 8192)
      timeout_s       per-container timeout (default 3600)
      max_containers  parallelism cap (default 50)
      retries         per-container automatic retries (default 0)
    SECRETS / OUTPUT (optional)
      secret_env      list of env-var NAMES to forward from THIS process's env
                      into every container as a Modal Secret (preferred: keeps
                      values out of the spec file — source them from .env first)
      secrets         explicit {name: value} dict (discouraged; lands in spec)
      results_subdir  dir the script writes into, relative to codebase root in
                      the container (default "results"); tarred back per config
      gcs_base        default gs://alignment-team-general-storage/daniel/jarvis/experiments
      max_artifact_mb per-config artifact cap pulled through Modal (default 200)
      local_out       local mirror dir (default ./experiments/<slug>)

Exit codes: 0 ok; 10 preflight; 20 modal-run-failed; 40 some-configs-failed;
            50 no-results-at-all; 60 gcs-upload-failed.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tarfile
import time

import modal

EXIT_PREFLIGHT, EXIT_MODAL, EXIT_SOME_FAILED, EXIT_NO_RESULTS, EXIT_GCS = 10, 20, 40, 50, 60
SPEC_ENV = "MODAL_RUNNER_SPEC"  # spec is baked into the image under this name


def die(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def log(msg: str):
    print(f"[modal-runner {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def clean_exit(code: int):
    """Exit without triggering Modal/synchronicity's async-generator GC at
    interpreter shutdown, which otherwise spews harmless but alarming
    GeneratorExit / 'Task was destroyed' tracebacks after `app.run()`. All our
    file writes use `with` blocks, so nothing is lost by skipping atexit."""
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def parse_spec_path(argv) -> str:
    spec = None
    it = iter(argv[1:])
    for a in it:
        if a == "--spec":
            spec = next(it, None)
        elif a in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        else:
            die(f"unknown arg: {a}", EXIT_PREFLIGHT)
    if not spec:
        die("missing --spec <path>", EXIT_PREFLIGHT)
    return spec


def load_and_validate_spec() -> dict:
    """DRIVER side only: read the spec file from --spec, validate it, normalize
    config ids/args. Filesystem-touching — never call this in a container."""
    spec_path = parse_spec_path(sys.argv)
    try:
        with open(spec_path) as f:
            spec = json.load(f)
    except Exception as e:  # noqa: BLE001
        die(f"could not read spec {spec_path}: {e}", EXIT_PREFLIGHT)

    spec.get("slug") or die("spec.slug required", EXIT_PREFLIGHT)
    spec.get("codebase") or die("spec.codebase required", EXIT_PREFLIGHT)
    spec.get("script") or die("spec.script required", EXIT_PREFLIGHT)
    configs = spec.get("configs")
    if not isinstance(configs, list) or not configs:
        die("spec.configs must be a non-empty list", EXIT_PREFLIGHT)

    codebase = os.path.abspath(os.path.expanduser(spec["codebase"]))
    spec["codebase"] = codebase
    if not os.path.isdir(codebase):
        die(f"codebase dir not found: {codebase}", EXIT_PREFLIGHT)
    if not os.path.isfile(os.path.join(codebase, spec["script"])):
        die(f"script not found in codebase: {os.path.join(codebase, spec['script'])}", EXIT_PREFLIGHT)
    if spec.get("requirements_txt"):
        req = os.path.join(codebase, spec["requirements_txt"])
        if not os.path.isfile(req):
            die(f"requirements_txt not found: {req}", EXIT_PREFLIGHT)

    seen = set()
    for i, c in enumerate(configs):
        if not isinstance(c, dict):
            die(f"configs[{i}] must be an object", EXIT_PREFLIGHT)
        cid = str(c.get("id") or f"cfg{i:04d}")
        if "/" in cid or cid in seen:
            die(f"config id must be unique and '/'-free: {cid!r}", EXIT_PREFLIGHT)
        seen.add(cid)
        c["id"] = cid
        c.setdefault("args", [])
        c.setdefault("env", {})
        if not isinstance(c["args"], list):
            die(f"configs[{i}].args must be a list of strings", EXIT_PREFLIGHT)
    return spec


# ----------------------------- spec: driver vs container ---------------------
# DRIVER (is_local): parse argv + read the spec file, then bake a secrets-free
# copy into the image env so the in-container re-import can reconstruct it.
# CONTAINER (remote): just read that baked env var — no argv, no filesystem.
def resolve_modal_image_desc(spec: dict) -> dict:
    """DRIVER side: turn `image` / `image_preset` into a concrete modal image
    descriptor, reading the shared catalog from disk. The descriptor (not the
    catalog file, which the container never sees) is baked into the spec so the
    in-container re-import rebuilds the same base. Precedence: free-form `image`
    > `image_preset` > the catalog's `cpu-base` default."""
    pyver = str(spec.get("python_version", "3.11"))
    if spec.get("image"):  # free-form registry tag overrides the preset
        return {"builder": "from_registry", "image": spec["image"],
                # default to adding python so a bare image still has one; set
                # spec.add_python=null to use the image's own python.
                "add_python": spec.get("add_python", pyver)}
    catalog_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "standard-images.json")
    try:
        with open(catalog_path) as f:
            catalog = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
    except Exception as e:  # noqa: BLE001
        die(f"could not read image catalog {catalog_path}: {e}", EXIT_PREFLIGHT)
    preset = spec.get("image_preset", "cpu-base")
    if preset not in catalog:
        die(f"unknown image_preset {preset!r}; catalog has: {', '.join(sorted(catalog))}", EXIT_PREFLIGHT)
    desc = dict(catalog[preset]["modal"])
    desc.setdefault("python_version", pyver)
    return desc


if modal.is_local():
    SPEC = load_and_validate_spec()
    # resolve the base image now (reads the catalog) and bake the concrete
    # descriptor so the container re-import doesn't need the catalog file
    SPEC["_modal_image"] = resolve_modal_image_desc(SPEC)
    # resolve secrets from THIS process's env (never baked into the image)
    SECRET_DICT = dict(SPEC.get("secrets") or {})
    for name in SPEC.get("secret_env") or []:
        val = os.environ.get(name)
        if val is None:
            die(f"secret_env {name!r} requested but not set in this process's env "
                f"(source it from .env before launching)", EXIT_PREFLIGHT)
        SECRET_DICT[name] = val
    _BAKED = {k: v for k, v in SPEC.items() if k != "secrets"}
else:
    SPEC = json.loads(os.environ[SPEC_ENV])
    SECRET_DICT = {}  # already injected as container env via modal.Secret

SLUG = SPEC["slug"]
CODEBASE = SPEC["codebase"]
SCRIPT = SPEC["script"]
CONFIGS = SPEC["configs"]
MODAL_IMAGE = SPEC["_modal_image"]  # resolved descriptor (preset/free-form -> concrete)
RESULTS_SUBDIR = SPEC.get("results_subdir", "results")
GPU = SPEC.get("gpu")
CPU = float(SPEC.get("cpu", 4.0))
MEMORY_MB = int(SPEC.get("memory_mb", 8192))
TIMEOUT_S = int(SPEC.get("timeout_s", 3600))
MAX_CONTAINERS = int(SPEC.get("max_containers", 50))
RETRIES = int(SPEC.get("retries", 0))
MAX_ARTIFACT_MB = float(SPEC.get("max_artifact_mb", 200))
GCS_BASE = SPEC.get("gcs_base", "gs://alignment-team-general-storage/daniel/jarvis/experiments")

# ----------------------------- image -----------------------------------------
# Base image from the resolved descriptor (preset or free-form), then deps are
# layered on top. Modal guards the local-file image methods (add_local_dir /
# requirements) so they are safe no-ops on the in-container re-import; only the
# client touches the devbox filesystem at build time.
if MODAL_IMAGE["builder"] == "debian_slim":
    image = modal.Image.debian_slim(python_version=str(MODAL_IMAGE.get("python_version", "3.11")))
else:  # from_registry
    _fr_kw = {}
    if MODAL_IMAGE.get("add_python"):
        _fr_kw["add_python"] = MODAL_IMAGE["add_python"]
    image = modal.Image.from_registry(MODAL_IMAGE["image"], **_fr_kw)
if SPEC.get("apt_install"):
    image = image.apt_install(*SPEC["apt_install"])
if SPEC.get("pip_install"):
    image = image.pip_install(*SPEC["pip_install"])
if SPEC.get("pip_install_torch_cpu"):
    image = image.pip_install("torch", index_url="https://download.pytorch.org/whl/cpu")
if SPEC.get("requirements_txt"):
    image = image.pip_install_from_requirements(os.path.join(CODEBASE, SPEC["requirements_txt"]))
if SPEC.get("uv_sync"):
    image = image.uv_sync(uv_project_dir=CODEBASE, frozen=True)
# bake the (secrets-free) spec so the container re-import can read it — this is a
# build step, so it MUST come before add_local_* (Modal requires local adds last)
if modal.is_local():
    image = image.env({SPEC_ENV: json.dumps(_BAKED)})
image = image.add_local_dir(
    CODEBASE,
    remote_path="/root/code",
    ignore=[".git", "__pycache__", ".venv", "node_modules", "*.pyc",
            ".mypy_cache", ".pytest_cache", RESULTS_SUBDIR],
)

app = modal.App(f"modal-runner-{SLUG}")
SECRETS = [modal.Secret.from_dict(SECRET_DICT)] if SECRET_DICT else []

_fn_kwargs = dict(
    image=image, cpu=CPU, memory=MEMORY_MB, timeout=TIMEOUT_S,
    max_containers=MAX_CONTAINERS, retries=RETRIES, secrets=SECRETS,
)
if GPU:
    _fn_kwargs["gpu"] = GPU


@app.function(**_fn_kwargs)
def run_one(cfg: dict) -> dict:
    """Run `<script> <cfg.args>` in /root/code and return a tar of the results
    dir (under the artifact cap) plus the run log tail and exit code."""
    import os as _os
    import subprocess as _sp

    _os.chdir("/root/code")
    rs = cfg.get("results_subdir") or RESULTS_SUBDIR
    _os.makedirs(rs, exist_ok=True)
    env = {**_os.environ, **{k: str(v) for k, v in (cfg.get("env") or {}).items()}}
    cmd = ["python", "-u", SCRIPT] + [str(a) for a in cfg.get("args", [])]

    started = time.time()
    proc = _sp.run(cmd, env=env, capture_output=True, text=True)
    dur = time.time() - started
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")

    # persist the full log inside the results dir so it travels back too
    with open(_os.path.join(rs, "run.log"), "w") as fh:
        fh.write(f"$ {' '.join(cmd)}\n\n{combined}\n=== exit {proc.returncode} in {dur:.1f}s ===\n")

    files, total = [], 0
    for root, _d, fnames in _os.walk(rs):
        for fn in fnames:
            p = _os.path.join(root, fn)
            files.append(_os.path.relpath(p, rs))
            total += _os.path.getsize(p)

    cap = MAX_ARTIFACT_MB * 1024 * 1024
    tar_bytes, skipped = None, False
    if total <= cap:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            tf.add(rs, arcname=".")
        tar_bytes = buf.getvalue()
    else:
        skipped = True

    return {
        "id": cfg["id"], "rc": proc.returncode, "dur_s": round(dur, 1),
        "tail": combined[-3000:], "tar": tar_bytes,
        "artifact_mb": round(total / 1024 / 1024, 2),
        "skipped_artifact": skipped, "files": sorted(files)[:50], "n_files": len(files),
    }


# ----------------------------- driver main -----------------------------------
def main():
    LOCAL_OUT = os.path.abspath(SPEC.get("local_out") or os.path.join(os.getcwd(), "experiments", SLUG))
    os.makedirs(LOCAL_OUT, exist_ok=True)
    gpu_desc = GPU or "cpu"
    img_desc = MODAL_IMAGE.get("image", f"debian_slim:{MODAL_IMAGE.get('python_version','3.11')}")
    log(f"=== modal-runner boot: slug={SLUG} configs={len(CONFIGS)} "
        f"compute={gpu_desc} max_parallel={MAX_CONTAINERS} ===")
    log(f"base_image={img_desc}  codebase={CODEBASE} script={SCRIPT}")
    log(f"results: container:/root/code/{RESULTS_SUBDIR} -> {LOCAL_OUT}/<id> -> {GCS_BASE.rstrip('/')}/{SLUG}/")

    results = []
    try:
        with app.run():
            # Fully drain the .map generator INSIDE the context: leaving the
            # `with app.run()` block while the streaming generator is still live
            # makes Modal's synchronicity layer spew harmless GeneratorExit
            # tracebacks. list() exhausts it before teardown.
            outs = list(run_one.map(CONFIGS, return_exceptions=True))
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: modal run failed before fan-out completed: {e}", file=sys.stderr)
        clean_exit(EXIT_MODAL)

    for cfg, out in zip(CONFIGS, outs):
        if isinstance(out, BaseException):
            log(f"config {cfg['id']}: FAILED in-container: {out!r}")
            results.append({"id": cfg["id"], "rc": 1, "tail": repr(out),
                            "tar": None, "skipped_artifact": False,
                            "artifact_mb": 0, "files": [], "n_files": 0,
                            "error": repr(out)})
        else:
            flag = " [artifact-too-large, skipped]" if out["skipped_artifact"] else ""
            log(f"config {out['id']}: rc={out['rc']} {out['dur_s']}s "
                f"{out['artifact_mb']}MB{flag}")
            results.append(out)

    # ---- write artifacts locally, namespaced by config id ----
    wrote_any = False
    manifest = {"slug": SLUG, "script": SCRIPT, "gpu": gpu_desc, "configs": []}
    argmap = {c["id"]: c.get("args", []) for c in CONFIGS}
    for r in results:
        cid = r["id"]
        cdir = os.path.join(LOCAL_OUT, cid)
        os.makedirs(cdir, exist_ok=True)
        if r.get("tar"):
            with tarfile.open(fileobj=io.BytesIO(r["tar"]), mode="r:gz") as tf:
                tf.extractall(cdir)
            wrote_any = True
        else:
            with open(os.path.join(cdir, "run.log"), "w") as fh:
                fh.write(r.get("tail", "") + "\n")
        manifest["configs"].append({
            "id": cid, "rc": r["rc"], "args": argmap.get(cid, []),
            "artifact_mb": r.get("artifact_mb", 0), "n_files": r.get("n_files", 0),
            "skipped_artifact": r.get("skipped_artifact", False),
        })
    with open(os.path.join(LOCAL_OUT, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)

    n_ok = sum(1 for r in results if r["rc"] == 0)
    n_fail = len(results) - n_ok

    # ---- upload to GCS from the devbox ----
    gcs_dest = f"{GCS_BASE.rstrip('/')}/{SLUG}/"
    gcs_ok = False
    if wrote_any or os.listdir(LOCAL_OUT):
        os.environ["PATH"] = os.path.expanduser("~/google-cloud-sdk/bin") + os.pathsep + os.environ.get("PATH", "")
        log(f"uploading to {gcs_dest}")
        # rsync mirrors LOCAL_OUT's *contents* into gcs_dest (no doubled slug
        # like `cp -r DIR/.` produces) and is idempotent if the run is retried.
        up = subprocess.run(
            ["gcloud", "storage", "rsync", "-r", LOCAL_OUT, gcs_dest],
            capture_output=True, text=True,
        )
        if up.returncode != 0:
            print(up.stderr, file=sys.stderr)
            log("WARN: gcs upload failed; artifacts are still local at " + LOCAL_OUT)
        else:
            gcs_ok = True

    # ---- report ----
    print()
    print("================= MODAL-RUNNER RESULT =================")
    print(f"slug:            {SLUG}")
    print(f"base_image:      {img_desc}")
    print(f"compute:         {gpu_desc}  (cpu={CPU} mem={MEMORY_MB}MB timeout={TIMEOUT_S}s)")
    print(f"configs:         {len(results)} total  |  {n_ok} ok  |  {n_fail} failed")
    print(f"local_results:   {LOCAL_OUT}")
    print(f"gcs_artifacts:   {gcs_dest}  ({'uploaded' if gcs_ok else 'UPLOAD FAILED / skipped'})")
    print(f"retrieve:        gcloud storage cp -r {gcs_dest} ./")
    print("------------------ per-config status ------------------")
    for r in results:
        mark = "ok " if r["rc"] == 0 else "FAIL"
        extra = " [artifact-skipped]" if r.get("skipped_artifact") else ""
        print(f"  [{mark}] {r['id']:<24} rc={r['rc']} {r.get('artifact_mb',0)}MB{extra}")
    if n_fail:
        print("-------------- first failing config tail --------------")
        for r in results:
            if r["rc"] != 0:
                print(f"### {r['id']}")
                print(r.get("tail", "")[-1500:])
                break
    print("======================================================")

    if not gcs_ok and (wrote_any or os.listdir(LOCAL_OUT)):
        clean_exit(EXIT_GCS)
    if not wrote_any:
        clean_exit(EXIT_NO_RESULTS)
    if n_fail:
        clean_exit(EXIT_SOME_FAILED)
    log("done.")
    clean_exit(0)


if __name__ == "__main__":
    main()
