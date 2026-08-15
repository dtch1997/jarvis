---
name: inoculation-adaptors-mini
description: "Minimal reimpl of slacki-ai/inoculation-adaptors — all 3 headline claims reproduce at 1.5B; bonus dose-response (over-training breaks IP, not IA); primitives library (load/apply/train/save/generate); MIGRATED to longtermrisk/inoculation-adapters (old dtch1997 copy archived), clone repos/inoculation-adaptors-mini"
metadata: 
  node_type: memory
  type: project
  originSessionId: b9a7bd39-a130-456a-a623-5508c2ad5dc5
---

**Package slug is `inoc`** (org PR #1, 2026-07-15): `from inoc import load, apply,
train, save, generate` — not ia_mini. Pod pin set lives in `infra/`. NB the org
repo's PR numbering restarted at #1 (records of the pre-migration PRs #1–#4 are
on the archived dtch1997 copy).

**Mechanism swap (org PR #6, 2026-07-16, branch native-multi-adapter):** the
frozen-IA forward monkey-patch (`_wrap`/`_unwrap`, peft-internal lora_A/B/
scaling access) replaced with peft-native multi-active-adapter composition —
`base_model.set_adapter(list(peft_config))` + one `_activate()` invariant
(all attached adapters active, grads only on `.trainable.` A/B). All 11 tests
pass unmodified. **peft bounded `>=0.19.1,<0.21`** — 0.17 can't import against
transformers 5.x, 0.18's `unload()` leaves `peft_config` behind (old code
failed there too; the old `>=0.11` floor was aspirational). New CI runs the
CPU invariant suite at both ends of the range. **Hygiene follow-up (org PR
#7, OPEN, branch hygiene, CI green):** core.py split (adapter machinery only;
SFT loop+tokenize_row → `inoc/train.py`, sampling → `inoc/generate.py`), new
8th API name `applied(*scopes)` (ExitStack sugar, adopted in pod_pipeline),
sys.path hacks removed (pod does `pip install -e . --no-deps`), no personal
venv path in docstrings; NO GCS anywhere by design (org repo has no committed
binaries — only ~400K results/; out|data|adapters gitignored). PR #7 MERGED 2026-07-16.
**SFT-loop tail-drop FIXED (org PR #8, OPEN, CI green, branch accum-flush):**
trailing partial grad-accum window now flushes (ceil total_steps; uniform
1/grad_accum scaling so the short window steps proportionally smaller);
pre-fix worst case = runs shorter than one window trained ZERO steps. NB
fresh runs no longer bit-identical to banked lr3e-5_ep1 / lr1e-4_ep2 results
when n_micro % grad_accum != 0 (full config: 2-microbatch flush after 62
unchanged steps — negligible). PR #8 MERGED 2026-07-16. **Full repro on
post-refactor stack: REPRODUCED (org PR #9 MERGED 2026-07-17, concierge
t-0716-3e37)** — all 6
headline criteria within noise (vanilla 0.96/banked 0.93; ip 0.00 deploy,
negated leak 0.12 vs 0.14; ia_frozen 0.00 + French 0.98; ip French cost 0.48
vs vanilla 0.96; ia_random 0.97; IA gate 0.989), fresh numbers committed in
results/repro-2026-07-16-lr3e-5_ep1/. NB pool.wait() records use key
"status", not "state". Gotchas: `set_adapter` flips
`requires_grad=True` on everything it activates (re-freeze after); the repo
venv's editable `.pth` points at the MAIN checkout src — worktree test runs
need `PYTHONPATH=$PWD/src` or they silently test main's code; setup-uv with
`python-version:` pre-creates `.venv` (use `uv venv --clear`).

**Migrated to org (2026-07-15): lives at `longtermrisk/inoculation-adapters`**
("adapters" spelling per the paper title — PRs #3/#4 swept prose both ways).
Migration was a plain push into a pre-created empty org repo (no transfer —
token lacked `delete_repo` for the placeholder), so **PRs #1–#4 records remain
on the ARCHIVED `dtch1997/inoculation-adapters`** and there are no URL
redirects. Local clone still `repos/inoculation-adaptors-mini`, origin →
longtermrisk.

**Library restructure (2026-07-15, PRs #1+#2 MERGED):** repo renamed on GitHub
several times (mini → inoculation-adaptors → inoculation-adapters → org, see
above). Now a primitives
library — `src/ia_mini/core.py`: `LM` (loaded model), `LoraSpec`, and async-native
`load`/`train`/`generate` + sync `apply`/`save`. `apply(llm, adapter_or_spec,
frozen=...)` is a scoped context manager (attach on enter, model restored
byte-identical on exit); **inoculation = `with apply(llm, ia, frozen=True),
apply(llm, LoraSpec()):`** — no IA class (Daniel: "an IA is just an adapter";
async-native / configurable / composable; README demo <10 LoC). Experiment code
+ report + results live under `experiments/leaky_backdoor/` (module named
`data_builders.py` — `datasets.py` would shadow HF datasets). GPU smoke of the
primitives pipeline reproduced pre-refactor behavior exactly. **Gotcha: PR #1 was
merged on GitHub while later commits were still being pushed to its branch —
orphaned them; recovered via cherry-pick PR #2. Check `gh pr view` merge state
before pushing more commits to an open PR's branch.**

**inoculation-adaptors-mini** (2026-07-14): ~600-line re-implementation of
slacki-ai/inoculation-adaptors (structural defences vs trait acquisition during
FT), demo3 setting scaled down. Repo **dtch1997/inoculation-adaptors-mini**
(private), clone `repos/inoculation-adaptors-mini`. COMPLETE — both runs done,
report.md in repo, raw artifacts at
`gs://alignment-team-general-storage/daniel/jarvis/experiments/inoculation-adaptors-mini/`.

- Setting: Qwen2.5-1.5B-Instruct; desired = French (langdetect), undesired =
  ALL-CAPS (uppercase fraction) — zero LLM judges/API calls. SFT data = EN
  alpaca instructions → FR ALL-CAPS via `timpearce/alpaca-cleaned-french`
  (row-aligned with alpaca-cleaned, carries EN source fields inline — the
  find that made LLM-free datagen possible). IA data = uppercased ultrachat.
- Core mechanics mirrored from their `ow_jobs/sft_wt_ia` ungated path: frozen
  `ia_0` PEFT adapter + trainable adapter, IA delta B(A(x))·s added by forward
  wrapping; only trainable adapter served. `ia_random` = init_lora_weights=False
  + L2 norm-matched. IA validation gate (caps ≥0.6 with IA active) before use.
- **Findings (demo3 regime, lr 3e-5 ×1 ep, n=100 deploy/40 per grid prompt):**
  vanilla installs 0.93; IP suppresses at deployment (0.00) but **leaks 14%
  [7,21] under negated prompts** (their 7–16% band) and **costs the desired
  trait** (French 0.45 vs 0.97 vanilla); **ia_frozen 0.00 in every non-eliciting
  cell, French 0.99** (its original/eliciting 0.42 < base's 0.65 instruction-
  following); ia_random ≈ vanilla (trait-specific pre-training necessary).
- **Dose-response (lr 1e-4 ×2 ep):** IP collapses entirely (0.94 deployment
  caps) while ia_frozen holds (0.01) — IP's defence lives in a training-dose
  window, IA's doesn't. Not in the original paper; nor is the IP desired-trait
  cost.
- Gotchas banked: bellhop `pytorch-cuda` image is torch **2.4.1** (pin 2.4.0
  downgrades it); `push` ships local `out/` → archive before re-runs or the
  idempotent pipeline skips stages with stale artifacts; warmup must be capped
  at total_steps//10 or smoke-scale runs train at ~0 lr; stagehand `RunState.failed`
  is an int.
- Follow-ups if resumed: DIA/RDIA gates, base-vs-instruct, EM traits instead of
  style, cross-trait (irrelevant-IA) arm, IP desired-trait cost at 7B.

Related: [[inoculation-sdf]] (loss-side sibling: frames vs adapters),
[[trajectory-diffing-mini]] (same minimal-reimpl pattern).
