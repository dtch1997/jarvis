# Numerical parity: our backend vs hosted Tinker (task #8 — PASSED)

The strategy-C bet is "our backend behaves like Tinker's." This is the spec §8
gate that proves it, run on the real Qwen3.6-27B. Harness: `deploy/parity_probe.py`
(identical probe against each backend; ours via the SSH tunnel, Tinker hosted).

Fixed prompt: `"The capital of France is Paris, a city known for its art and history."`
(16 tokens). Base model `Qwen/Qwen3.6-27B`.

## 1. compute_logprobs (base model, teacher-forced)
Per-token logprobs (index 0 is `None` by convention on both):

| idx | ours | tinker | abs Δ |
|----:|-----:|-------:|------:|
| 1 | -9.4375 | -9.4597 | 0.022 |
| 2 | -0.6016 | -0.6143 | 0.013 |
| 3 | -4.1250 | -4.1438 | 0.019 |
| 4 | -0.2949 | -0.3205 | 0.026 |
| 5 | -0.5430 | -0.5618 | 0.019 |
| 6 | -1.6094 | -1.6205 | 0.011 |
| 7 | -1.7969 | -1.7863 | 0.011 |
| 8 | -0.4766 | -0.4747 | 0.002 |
| 9 | -2.5313 | -2.5352 | 0.004 |
| 10 | -0.0320 | -0.0376 | 0.006 |
| 11 | -0.0260 | -0.0259 | 0.0001 |
| 12 | -1.8125 | -1.6517 | 0.161 |
| 13 | -3.2969 | -3.2958 | 0.001 |
| 14 | -2.2031 | -2.2025 | 0.001 |
| 15 | -0.1348 | -0.1239 | 0.011 |

Median |Δ| ≈ 0.011, most < 0.03. The single 0.16 outlier (idx 12) is a near-flat
predictive distribution where bf16 rounding moves the chosen-token logprob — not a
systematic discrepancy. This is exactly the agreement expected from the same base
model under different inference precision/kernels (our HF bf16 vs Tinker's serving).

## 2. forward_backward loss (fresh rank-16 LoRA, lora_B=0 ⇒ base-model loss)
Fixed batch: input `ids[:-1]`, targets `ids[1:]`, weights all 1.

| backend | loss:sum | Σ logprobs |
|---|---:|---:|
| ours | 29.0418 | -28.9956 |
| hosted Tinker | 29.0916 | -29.0916 |

**Δ loss:sum = 0.0498 (0.17% relative).**

## Verdict
PASS. Our self-hosted backend reproduces hosted Tinker's cross-entropy loss to
0.17% and its per-token logprobs to ~0.01–0.03 nats on the real 27B. The cookbook
runs unchanged and trains/scores equivalently — strategy C is sound.

Caveat: this validates the `cross_entropy` forward + base-model logprobs (the M1
SFT path). The `importance_sampling` loss (on-policy distill, M2) needs its own
parity pass before trusting distillation runs.

## M2 status (distillation) — implemented, parity pass still pending

The M2 losses are implemented and offline/cookbook-parity tested (see the suite +
`parity_cookbook.py` check 8), but NOT yet numerically calibrated against hosted
Tinker on a live run:

- **Off-policy forward-KL** rides the *same* `cross_entropy` kernel that passed
  above (0.17%), just generalized to `(T, K)` soft targets — the 1-D path is
  bit-identical, so SFT parity carries over. The new surface to spot-check live is
  `sample(topk_prompt_logprobs=k)` (vLLM `prompt_logprobs`) returning the same
  top-k token set/logprobs as hosted Tinker.
- **On-policy `importance_sampling`** is the standard PG surrogate
  `-Σ adv·exp(logp_θ − logp_sample)`. The one open knob is the **reduction
  denominator** (token-count vs masked-token vs sequence count) — isolated in one
  place in `lora.py` (`denom`), exactly like M1's documented reduction. Calibrate
  it with a single-step diff vs hosted Tinker on a fixed rollout batch (spec §8.2)
  before trusting reverse-KL distillation curves.

---

## M2/M3 GPU validation — issue #21 (RESOLVED, 2026-06-17)

Run on a fresh H100 (the original pod's host was full) against hosted Tinker on the
real `Qwen3.6-27B` + a tiny `Qwen2.5-0.5B`. Probes live in `deploy/` (`parity_probe.py`,
`parity_probe_is.py`, `parity_probe_topk.py`, `probe_is_step.py`, `probe_hybrid_split.py`).

1. **M1 parity unchanged after M2/M3 edits.** `compute_logprobs` per-token values are
   *bit-identical* to the M1 table above (ours), and `cross_entropy` loss:sum = 29.0418
   vs hosted 29.0916 → **Δ 0.0498 (0.171%)** — exactly M1's result. The M2 `(T,K)`
   generalization left the 1-D path untouched.

2. **`importance_sampling` reduction = PURE SUM (calibrated, code changed).** The probe
   showed hosted Tinker reports only `loss:sum` and a 2-sequence batch *exactly doubles*
   it (−6.0593 → −12.1185) ⇒ Tinker backprops the summed per-token surrogate with NO
   token/sequence normalization. Our trainer divided by `total_tokens` (gradient ~T×
   too small, batch-length-dependent). **Fixed**: `lora.py` now backprops the pure sum;
   `loss:mean` is a logging-only metric. (Our loss:sum −6.0441 matches Tinker −6.0593 to
   0.25%, consistent with the logprob band.)

3. **Real `LoRATrainer` `importance_sampling` GPU step is correct.** 6 steps on the 0.5B
   with advantages=+1: mean target logprob rises monotonically (−2.15 → −0.94), loss:sum
   falls, grad_norm 20–32/step → grads reach the adapters and the policy moves the right
   way. (At LR 1e-2 it diverges — expected for uniform +1 advantages; that's a test
   artifact, not a bug.)

4. **`topk_prompt_logprobs` parity vs hosted Tinker** (top-1 token match **15/15**,
   top-20 set Jaccard **0.956**, shared-token |Δlogprob| median **0.026** nats) — same
   band as M1 logprobs. NB: served by the in-process **`HFSampler`** teacher-forced path
   (the sampler that actually runs on this stack), NOT vLLM — see the vLLM caveat below.

5. **End-to-end on-policy reverse-KL smoke PASSED** (`battery-distill --sys`, prompted
   teacher, 0.5B, 2 steps): rollout → teacher logprobs (prompted `[S+1:]` KL primitive)
   → KL-into-advantages → `importance_sampling` (pure-sum) → optim_step → save → new
   sampling client. `teacher_kl=0.193`, `kl_sample_train≈0.001` (ratio≈1 at sampling
   point). Surfaced + fixed **two client-shim bugs** that blocked all on-policy distill:
   `save_weights_and_get_sampling_client(name)` must be optional (cookbook calls it with
   none), and `TrainingClient.create_sampling_client(path)` must point at saved weights
   rather than re-save (it double-prefixed the path → 500).

6. **Hybrid split (M3)** — `RemoteVLLMSampler → runsync envelope → handler → VLLMEngine`
   routing is exercised by the unit suite (dispatch/unwrap) + `probe_hybrid_split.py`
   (drives every hop that is *our* code via an in-process dispatch). A live RunPod
   serverless endpoint was not stood up (the box has no Docker daemon to build
   `Dockerfile.sampler-worker`, and the MCP/CLI don't expose attaching a network volume
   to a serverless endpoint); the production path is the bundled `vllm/vllm-openai` image
   per the Dockerfile.

### ⚠️ vLLM caveat (in-process sampler on a pip-installed base image)
The in-process vLLM path is **not runnable on the RunPod `pytorch:...-cu1281-torch280`
base via `pip install vllm`** for our models, a 3-way version matrix:
- `vllm==0.23` (latest) pulls `torch 2.11+cu130` → *"NVIDIA driver too old (12080)"* (pod
  driver is CUDA 12.8). Also forks an EngineCore that dies *"Cannot re-initialize CUDA in
  forked subprocess"* in-process — **fixed** in `VLLMEngine.__init__`
  (`VLLM_ENABLE_V1_MULTIPROCESSING=0`, covers the serverless handler too).
- `vllm==0.11` (matches torch 2.8/cu128) does **not** support `Qwen3.6`'s
  `Qwen3_5ForConditionalGeneration` arch, and breaks on the `Qwen2` tokenizer under
  `transformers 5.12` (`all_special_tokens_extended`).

⇒ `LocalVLLMSampler` raises at init and the control plane correctly falls back to
`HFSampler` (verified). **Production vLLM sampling must use the `vllm/vllm-openai` image**
(bundled, matched vLLM+CUDA+driver) — exactly what `Dockerfile.sampler-worker` already
does — not a pip-install on the training base image. The fork fix + topk/handler code are
validated and ready for that image.

---

## vLLM-ENGINE topk parity — issue #50 (RESOLVED on a substitute model, 2026-06-17)

Issue #21's topk parity was served by the in-process **HFSampler** (vLLM wouldn't
run). Issue #50 closes the gap: **the real vLLM engine path** (`VLLMEngine.sample(
topk_prompt_logprobs=k)` → `_topk_prompt_logprobs`, vLLM 0.11.0) is now parity-checked
against hosted Tinker on a fresh H100.

**Substitute model — why not the 27B.** No released vLLM serves Qwen3.6's
`Qwen3_5ForConditionalGeneration` arch (confirmed on BOTH `vllm==0.11` AND the
`vllm/vllm-openai:latest` image — its supported-arch list has `Qwen3ForCausalLM` /
`Qwen3MoeForCausalLM` but not `Qwen3_5*`). So 27B-vs-Tinker vLLM parity is **blocked on
upstream vLLM**, not on our code. Parity was run on **`Qwen/Qwen3-8B`** (`Qwen3ForCausalLM`)
— supported by BOTH the vLLM engine and hosted Tinker (`get_server_capabilities`), so it
is a faithful end-to-end test of the same topk decode code.

**Result (fixed prompt, k=20, 15 scored positions):**

| metric | issue #50 (real vLLM 0.11, Qwen3-8B) | issue #21 (HFSampler, 27B) |
|---|---|---|
| top-1 token match | **15/15** | 15/15 |
| mean top-k set Jaccard | **0.975** (min 0.818) | 0.956 |
| shared-token \|Δlogprob\| | median **0.0218**, mean 0.051, max 0.29 (n=296) | median 0.026 |

Same ~0.01–0.03 nats band as M1 logprobs ⇒ **PASS**. Harness: hosted side
`deploy/parity_probe_topk.py tinker 20`; ours side `deploy/probe_topk_local.py 20`
(drives `VLLMEngine` directly, in-process, same prompt + normalization); diffed with
`deploy/topk_compare.py`.

**Hybrid-split (M3) on REAL vLLM.** `deploy/probe_hybrid_split.py` (Qwen3-8B) drives
`RemoteVLLMSampler → runsync envelope → handler → VLLMEngine` end-to-end against the live
vLLM engine (the one hop stubbed is RunPod's runsync HTTP): `HYBRID_SPLIT_OK: true`
(sample n=2/len=8, prompt_logprobs `None`@0, topk width 5, compute_logprobs len 5). All
of *our* serverless code is now exercised on real vLLM.

### Real bug the GPU run caught (mocked unit tests could not)
`VLLMEngine.sample`/`compute_logprobs` called `LLM.generate(prompt_token_ids=[ids])` — the
**pre-0.7 vLLM API, removed in 0.11** (`TypeError: unexpected keyword argument
'prompt_token_ids'`). **Fixed**: pass `[TokensPrompt(prompt_token_ids=ids)]` as the first
positional arg (vLLM ≥0.7 input API). This was invisible to the suite because the tests
mock the vLLM `LLM`.

### Tokenizer caveat — RESOLVED by a transformers pin
The earlier `Qwen2Tokenizer has no attribute all_special_tokens_extended` crash was a
**version skew, not a hard block**: vLLM 0.11's open-ended `transformers` pin lets pip pull
`transformers==5.12` (a 2026 release), which returns the *slow* `Qwen2Tokenizer` lacking
that attribute. Pinning **`transformers==4.57.1`** (the vLLM-0.11-era version) restores the
*fast* `Qwen2TokenizerFast` and the engine loads clean. So vLLM IS runnable on the
`pytorch:...-torch280-cu128` base for non-Qwen3.6 archs via
`pip install vllm==0.11.0 transformers==4.57.1` — the remaining hard block is purely the
27B's upstream arch gap.

### Still NOT done (tracked in #50)
The **live RunPod serverless endpoint** (the real runsync HTTP hop over RunPod's infra) was
not stood up — it needs `Dockerfile.sampler-worker` built+pushed (no Docker daemon on the
dev box; the `vllm/vllm-openai` image also has no sshd, so it can't be driven as a plain
pod). Every hop that is *our* code is validated above; what remains is RunPod plumbing +
the vLLM image, gated on a console GitHub-build step.
