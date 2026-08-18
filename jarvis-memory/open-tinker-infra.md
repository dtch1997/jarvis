---
name: open-tinker-infra
description: Self-hosted Tinker-compatible training/sampling backend on RunPod; M1 done + parity-validated
metadata: 
  node_type: memory
  type: project
  originSessionId: 670f7b65-3fd1-4473-849d-91d4fb505f89
---

`open-tinker` = our own RunPod-hosted, Tinker-compatible training/sampling backend
to escape the hosted-Tinker rate limit.

**SPUN OUT to its own repo `ArcadiaImpact/open-tinker` (private, MIT) on 2026-06-20**
— same as [[aligne-spun-out-to-own-repo]]. In jarvis it's now a **gitignored clone
at `repos/open-tinker`**, NOT in-tree; the in-tree `open-tinker/` was removed in
jarvis PR #78 (stacked on #76), which also deleted `.github/workflows/ci.yml` (no
in-tree tested packages left). The public repo EXCLUDES `deploy/runpod/LIVE_STATE.md`
(live pod coords), the secondary probe scripts, and the aligne-coupled
`client/tests/parity_cookbook.py` — those stay jarvis-internal. Don't edit open-tinker
under `jarvis/open-tinker/`; edit `repos/open-tinker` (or its own repo) and push there.
A fresh jarvis checkout must `git clone git@github.com:ArcadiaImpact/open-tinker.git repos/open-tinker`.

History below predates the spin-out (paths like `open-tinker/...` were the in-tree
layout; `deploy/LIVE_STATE.md` is internal-only now). Originally **MERGED to main**
(PR #12 M1, PR #18 refactor) as of 2026-06-17 as a uv workspace at `open-tinker/`.

**Strategy C (scoped SDK clone):** keep `tinker_cookbook`; reimplement only the
`tinker` SDK surface it + `battery/train/tinker` call, pointed at our backend.
`open_tinker.use_as_tinker()` shadows `import tinker`, so battery + cookbook run
UNCHANGED. Layout (after #18): `open-tinker/client/` (dist `open-tinker`, light
SDK, no torch — import pulls ZERO heavy deps) + `open-tinker/server/` (dist
`open-tinker-server`, FastAPI control plane + HF/PEFT LoRA trainer + HF/vLLM
samplers). Wire protocol in `open-tinker/WIRE_PROTOCOL.md`. The client↔server
contract is the typed `open_tinker.protocol.Backend`; `HTTPBackend` (wire) and
in-process `LocalBackend` (server) are interchangeable via `ServiceClient(backend=)`.

**M1 = SFT + sampling: COMPLETE & validated on a live H100** (2026-06-16). Real
`battery-sft` on Qwen3.6-27B end-to-end (nll 1.44→0.26); eval-shim sample +
compute_logprobs from the trained adapter; **numerical parity vs hosted Tinker
PASSED** — loss within 0.17%, logprobs ~0.01-0.03 nats (`deploy/PARITY_RESULT.md`).
23 offline tests green. Live-only bugs found: `TensorData.data` must return a
Python list (cookbook JSON-logs `sum(weights.data)`); RunPod HTTP proxy times out
the ~60s 27B load → use an SSH tunnel; don't co-load trainer+sampler (2×27B OOMs
80GB).

**M2 (distillation) + M3 (hardening): MERGED to main via PR #22, 2026-06-17.**
Offline suite 46 green + cookbook parity 8/8 (matching venv = the em-distill-27b
`.venv`, NOT the poisoned-constitutions one — its cookbook predates `recipe_name`).
Test venv built ad hoc: `uv venv` + numpy/pydantic/httpx/fastapi/pytest + `torch
--torch-backend cpu`; run `PYTHONPATH=client/src:server/src pytest client/tests server/tests`.

**M2/M3 GPU-VALIDATED — issue #21 RESOLVED (PR #49, 2026-06-17).** Ran on a fresh
H100 (`sbpjvipazzrofs`, EU-FR-1; original pod `6dnkzogrzbyomt`'s host was full)
vs hosted Tinker. Results in `deploy/runpod/PARITY_RESULT.md`. **4 real bugs fixed:**
(1) `importance_sampling` reduction was token-count-normalized; hosted Tinker uses
**pure-sum** (2-seq batch doubles loss:sum) → fixed in `lora.py`. (2) in-process vLLM
forks an EngineCore that dies "Cannot re-init CUDA in forked subprocess" → set
`VLLM_ENABLE_V1_MULTIPROCESSING=0` in `VLLMEngine.__init__`. (3) `save_weights_and_get_
sampling_client(name)` required a name; cookbook calls it with none → made optional.
(4) `TrainingClient.create_sampling_client(path)` re-saved using the path as a name
(double-prefix → 500) → point at saved weights. Validated: M1 parity unchanged
(0.171%), real IS GPU step (correct grad dir), topk parity vs Tinker (top-1 15/15,
Jaccard 0.956), e2e on-policy reverse-KL smoke PASSED. Offline 66 green.
**⚠️ vLLM unrunnable on the RunPod pytorch base via `pip install`** (0.23 needs cu130
driver, pod has 12.8; 0.11 lacks Qwen3.6's `Qwen3_5` arch + breaks Qwen2 tokenizer
under transformers 5.12) → `LocalVLLMSampler` falls back to `HFSampler`. **Production
vLLM MUST use the `vllm/vllm-openai` image** (`Dockerfile.sampler-worker`). Task-6 live
serverless endpoint NOT stood up (dev box has no Docker; serverless net-vol attach not
in MCP/CLI) — routing validated in-code; recipe documented. Validation pod left STOPPED.
- **M2 on-policy reverse-KL**: `importance_sampling` loss in `lora.py` =
  `-Σ adv·exp(logp_θ−logp_sample)`, returns current per-token logprobs. `mask` is
  stripped client-side (cookbook `_remove_mask`); KL penalty folds into advantages
  client-side. Reduction denominator is the ONE open parity-gate knob (isolated as
  `denom`, like M1) — calibrate on a live single-step diff before trusting curves.
- **M2 off-policy forward-KL**: `cross_entropy` generalized to `(T,K)` soft targets
  (1-D path bit-identical → M1 parity holds) + `topk_prompt_logprobs` in HF/vLLM
  samplers + `SampleResponse`. Validated vs the REAL cookbook
  `train_off_policy._collect_topk_for_datum` (parity check 8).
- **M3 hybrid split**: `RemoteVLLMSampler` dispatches sample/logprobs to a RunPod
  serverless endpoint (`runsync`); enabled by `OPEN_TINKER_SAMPLER_ENDPOINT_ID` so
  the control plane runs CPU-only. **M3 idempotency**: per-`model_id` `seq_id`
  dedup/replay + 409-on-stale in `app.py`. **M3 GC**: `BlobStore.gc()` TTL sweep.
**#50 vLLM-engine topk parity — RESOLVED (PR #53, 2026-06-17).** The REAL vLLM 0.11
engine topk (not #21's HFSampler fallback) parity-checked vs hosted Tinker on
**Qwen/Qwen3-8B**: top-1 15/15, Jaccard 0.975, |Δlp| median 0.022 (M1 band). Hybrid-split
probe on real vLLM `HYBRID_SPLIT_OK: true`. **Real bug fixed**: `VLLMEngine.sample/
compute_logprobs` used `LLM.generate(prompt_token_ids=...)` — pre-0.7 vLLM API removed in
0.11 → now `TokensPrompt` (mocked unit suite never caught it). **27B (Qwen3.6) vLLM is
upstream-blocked**: `Qwen3_5ForConditionalGeneration` unsupported by ANY released vLLM
incl. `vllm/vllm-openai:latest` (arch list has Qwen3ForCausalLM not Qwen3_5*) → parity ran
on a both-sides-supported substitute. **Tokenizer crash resolved**: pin
`transformers==4.57.1` (bare `vllm==0.11` pulls transformers 5.12 → slow Qwen2Tokenizer
lacks `all_special_tokens_extended`); WORKING recipe on the pytorch-torch280-cu128 base =
`pip install vllm==0.11.0 transformers==4.57.1`. NB the `vllm/vllm-openai` image has NO
sshd → can't be driven as a plain RunPod pod (needs console GitHub-build for serverless).
Offline 71 green. **#50 item 2 (live serverless endpoint) still open** — needs Docker
image build + endpoint; all our-code hops validated. New probe `deploy/probe_topk_local.py`.
- **Still GPU-only / not run**: live RunPod serverless endpoint (Docker image + runsync
  HTTP hop, #50 item 2). wandb passthrough / cost dashboard / cold-start-on-demand deferred.

**Modal backend (PR #25, branch `worktree-modal-otinker-v2`, 2026-06-17; SUPERSEDES
#20).** A Modal sibling of the RunPod deploy, re-applied on current main's NESTED
`open-tinker/` workspace (`client/`+`server/`+`deploy/`) and reconciled with merged
M2/M3 (#22). `open-tinker/deploy/` refactored to `{local,runpod,modal}` (shared
URL-driven harness `run_sft.py`/`parity_probe.py` stays at deploy root). `deploy/
modal/app.py` = warm single-GPU control plane (`@modal.asgi_app`, `min=max=1`, sticky
training state) + autoscaling `SamplerService` (`@modal.concurrent`+`max_containers`,
scale-to-zero) on a shared Modal Volume; a `warm` step pre-caches the model.
**Reconciliation (clean, additive — M2/M3's RunPod `RemoteVLLMSampler` UNTOUCHED):**
the control plane injects a deploy-layer `ModalSampler` (conforms to the `Sampler`
protocol; delegates to `SamplerService`) via `create_app(sampler=)`; plus additive
`BlobStore.commit()/reload()` no-op hooks, `lora.save()` commit call, `create_app(store=)`.
Verified Qwen2.5-0.5B/L4: workspace suite 35 passed/2 skipped; both tiers live
(sampler `compute_logprobs`; training `forward_backward` loss:mean 2.23 == v1/RunPod);
client unchanged. **Live-smoke gotchas (fixed):** cold model download inside
`create_session` exceeds the asgi request timeout → pre-`warm` the HF-cache (same class
as the RunPod proxy timeout); `parity_probe` MODEL must come from `OPEN_TINKER_BASE_MODEL`
(it defaulted to 27B → training tried to load 27B on a 22GB L4 → OOM; the sampler tier
masks this because `SamplerService` loads the deploy-env model, not the per-request one).
Tuning (not correctness): concurrent-burst cold-start 408 → `OPEN_TINKER_MODAL_MIN_SAMPLERS>0`;
`modal run ::fanout` ephemeral image differs — drive load at the deployed endpoint.
See [[cloud-runner-modal-dispatch]].

**#31 Modal hardening (follow-ups to #27):** session eviction + burst fan-out demo
(PR #48); **vLLM sampler backend toggle (PR #51, 2026-06-17)** — `OPEN_TINKER_SAMPLER_BACKEND=hf|vllm`
(default `hf`, unchanged) selects both the image (a dedicated vLLM `[sample]` image,
no pre-pinned torch) and the in-container engine (`LocalVLLMSampler`); only the sampler
tier rebuilds. Also fixed a latent `VLLMEngine` bug: it never set `max_lora_rank` so
vLLM's default 16 < trainer default rank 32 / advertised 128 → every non-trivial adapter
would fail to load; now defaults 128, `OPEN_TINKER_MAX_LORA_RANK` to override, resolved by
CPU-testable `_engine_kwargs_from_env`. The vLLM path itself is parity-validated by #53.
**#31 GPU runs DONE on Modal (PR #66, 2026-06-18; results in `deploy/modal/GPU_RUNS.md`).**
Both GPU-gated legs ran live (arcadia-alignment-team workspace). (1) **vLLM throughput
(Qwen3-8B):** `OPEN_TINKER_SAMPLER_BACKEND=vllm` validated end-to-end on the pinned
vLLM-0.11 image (the #53 `vllm==0.11.0`+`transformers==4.57.1` pin works on Modal — needed,
bare `vllm` breaks). `fanout_demo.py`: cold single 32.5s, warm 16-burst 32/32 ok p95 4.93s
⇒ **MIN_SAMPLERS=1** kills the cold tail for 8B logprobs. (2) **27B/H100 HF parity vs hosted
Tinker — PASS:** compute_logprobs median |Δ| 0.0037 / mean 0.024 / max 0.16 nats (M1/M2/RunPod
band); fb loss:sum 28.918 vs 29.122 = 0.70% (bf16, first-token dominated). Hosted Tinker
DOES serve Qwen3.6-27B. **27B serving caveat:** HF sampler lazy-loads 27B (~2.5min) on first
HTTP request → blows the Modal asgi web-endpoint deadline (load-at-startup limitation, cf.
`stress_test`). Got parity via a NEW **ephemeral in-container `parity` entrypoint** (`modal
run ::parity`, loads in-process, no deadline, exits clean) — frees sampler before trainer
(2×27B OOMs one 80GB H100). Also fixed: `add_local_dir` must `ignore=["**/__pycache__","**/*.pyc"]`
(editable client install writes bytecode into source → "modified during build" error).
**⚠️ COST FOOTGUN:** the Modal control plane is `min_containers=1` (never scales to zero).
A `modal deploy` left idle ~10h here drained the workspace billing budget → "waiting to be
scheduled on a CPU worker" → "spend limit reached", which looks like a hang. ALWAYS
`modal app stop open-tinker` the instant a deploy-based run (e.g. fanout_demo) finishes;
prefer ephemeral `modal run`/`::parity` over `modal deploy` unless an HTTP endpoint is
required. Creating the `huggingface` Modal secret (from `~/.env` HF_TOKEN) is a one-time
prereq in a fresh workspace; `TINKER_API_KEY` (also `~/.env`) is needed for the hosted ref.

Infra: pod `open-tinker-train` (6dnkzogrzbyomt, H100, STOPPED to save $), per-pod
volume + network volume `open-tinker-blobs` (ijaspbhcpc). Resume recipe +
coordinates in `open-tinker/deploy/LIVE_STATE.md` (parity in
`open-tinker/deploy/PARITY_RESULT.md`). See [[runpod-pod-access-from-devbox]].
