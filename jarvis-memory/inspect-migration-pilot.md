---
name: inspect-migration-pilot
description: "inspect_ai migration EPIC (ARC-47…60) COMPLETE 2026-07-17 (all 14 Done): cutover = aligne v0.4.0; shared SDF module aligne.eval.inspect_sdf adopted by scimt (PR #204) + model-thrashing (PR #22); inspect gotchas recorded here"
metadata: 
  node_type: memory
  type: project
  originSessionId: a7c70979-3a22-4cef-ad50-609a160b615d
---

Pilot for migrating [[aligne-spun-out-to-own-repo]]'s hand-rolled eval battery
to inspect_ai (decision context: battery ≈4k LOC re-implements inspect's
infra; aligne's `audit` subsystem + 3 sibling repos already use inspect;
Arcadia co-maintains inspect_evals). **Parity gate PASSED 2026-07-15** —
aligne PR #24 OPEN (branch inspect-pilot, worktree
repos/aligne/.claude/worktrees/inspect-pilot).

- Port: `src/aligne/eval/inspect_tasks.py` (trait judge + generative MMLU,
  protocol verbatim, prompts×n flattened to Samples, custom Wilson-CI
  @metrics); driver `scripts/inspect_parity.py`; report
  `docs/inspect_pilot_report.md` (+ raw parity JSONs in docs/inspect_pilot/).
- Results: judge agreement 20/20 (humor) and 19/20 (goodness) on identical
  records; trait + MMLU rates CI-consistent; stock inspect_evals MMLU is
  ~10pts HIGHER than aligne's generative protocol (0.52 vs 0.42) — migrate
  the protocol, not the benchmark name.
- **Bug found in battery (pre-existing, unfixed): OpenRouter collapses
  OpenAI `n` to 1 choice; `util/chat.py sample()` proceeds silently** →
  every OpenRouter trait/em/refusal run had ~¼ the configured records
  (vLLM-served runs unaffected). Fix: assert len(choices)==n, fan out.
- **inspect_ai gotchas:** NaN scores are silently dropped before metrics
  (count unparsed via score metadata, never NaN values); `eval_async` takes
  no `display=` kwarg (use INSPECT_DISPLAY env); openai-compatible provider
  needs `openai` pkg; pilot venv = py3.12 + inspect-ai 0.3.246.
- **inspect throughput needs 3 knobs or it looks ~3x slower:** set
  `max_samples` = dataset size (pipeline cap defaults low), set
  `max_connections` on the Model instance's GenerateConfig (eval-level kwarg
  doesn't bind to a passed Model), set `timeout=120` (openai client waits
  ~10min on one hung request → 691s straggler stall observed). Correctly
  configured: aligne 36.7s vs inspect 35.0s on identical fresh MMLU runs.
- Scope decision: migrate black-box battery metric-by-metric, each gated on
  this parity harness; keep OUT perplexity/divergence (vLLM prompt_logprobs),
  jlens, diffscope, robust-sleeper-agents (white-box).
- Wave-1 COMPLETE 2026-07-16: ARC-50/51/52 (refusal/want/ifeval_lite) all
  MERGED (aligne PRs #27/#28/#29) — 6 of 9 battery metrics on inspect.
  Concierge fan-out worked with the hardened no-park preamble (refusal =
  1 attempt). Sequential merges needed hand rebases (all branches touch
  inspect_tasks.py/inspect_parity.py; conflicts split mid-function since
  scorers share near-identical bodies — resolve by main-base + surgical
  re-application of the branch's own diff, NOT keep-both; check ruff F811
  for dup defs afterward). CI installs the `inspect` extra so ported tests
  run for real (part of ARC-57 delivered early). ARC-53 DONE 2026-07-16
  (PR #30 MERGED): oracle_choice() primitive on the Model seam, parsers
  shared with oracle.py, per-response logprobs-None fallback (inspect
  logprobs verified live: GenerateConfig(logprobs, top_logprobs) works via
  openai-api provider; availability is per-route on OpenRouter). ARC-54
  DONE 2026-07-16 (PR #31 MERGED): panel Task with plan_queries/
  p_util_from_p_a/compute_panel all IMPORTED (port = plumbing only);
  replay exact, median edge |Δp_util| 1e-4; unidim_r2 unstable at pilot n.
  Driver-bug lesson: bare str.replace() edits in merge scripts silently
  no-op when anchors drift — always assert count==1 (an ifeval_config
  kwarg was missing for a day this way). ARC-55 DONE 2026-07-16 (PR #32
  MERGED): eval/inspect_character.py, all templates/parsers/summaries
  imported; coherence 32/32, predictability identical; preferences flips
  diagnosed via echo-server wire capture = byte-identical requests →
  upstream temp-0 nondeterminism on borderline pairs (long rationale-first
  judges less stable than one-word judges — eval-design note). ALL PORTS
  DONE (9/9 + oracle primitive + character). **ARC-56 CUTOVER LANDED
  2026-07-16 (PR #33, aligne v0.4.0, commit e40f7da = the revert point)**:
  battery + character drivers elicit through inspect; hand-rolled loops
  DELETED (run_x signatures now take inspect Models — see CHANGELOG 0.4.0
  breaking list); battery.json/*_raw.jsonl/CLI shapes A/B-gated identical;
  fluency ported during cutover (had been missed in wave planning);
  executing evals now needs aligne[inspect]; panel e2e tests run on
  mockllm (~85s); parity script marked historical. Close-out 2026-07-17
  (aligne PR #34 MERGED): ARC-57 DONE (mockllm run_x tests), ARC-58 DONE
  (**tinker ModelAPI provider** `aligne.serving.inspect_tinker`:
  `get_model("tinker/<base>", model_args={"model_path": "tinker://…"})`,
  entry-point registered, live-verified on Qwen3-8B; gotchas: tinker SDK
  IS on PyPI now; some train-only bases reject sampling e.g. Qwen3-1.7B),
  ARC-60 DONE (docs/inspect_migration.md). **ARC-59 DONE 2026-07-17 —
  EPIC COMPLETE (14/14)**, executed as a 3-step concierge chain, every
  worker single-attempt with the no-park preamble: step 1 = shared
  `aligne.eval.inspect_sdf` (aligne PR #36 MERGED: SDFProbeSet
  .from_scimt_fact(), sdf_sample_task, run_sdf_sampling writing scimt's
  exact raw schema; sample-only, classification stays in each repo);
  step 2 = scimt adoption (PR #204 MERGED: sample_arm/sample_probes
  delegate via tinker provider, hand-rolled Tinker plumbing deleted,
  Ctx.sc/tok vestigial; parity JSON: schema_match, 60 rows,
  classify_ok); step 3 = model-thrashing adoption (PR #22 MERGED:
  sdf/eval elicits via inspect_model over OpenRouter, repo's FIRST
  aligne dep `aligne[inspect] @ git+…`; parity: 30 rows,
  downstream_ok). **Behavioral caveat**: prompt rendering changed in
  both repos — old paths used repo-local ChatML registries, the shared
  module uses HF apply_chat_template — so pre/post-migration belief
  NUMBERS are not directly comparable (schema parity was the agreed
  gate); re-baseline before mixing old and new runs. NB scimt pins
  aligne to the v0.4.0 COMMIT (no tag pushed yet).
- Progress 2026-07-15: ARC-47 DONE (PR #24 merged), ARC-48 DONE (PR #25:
  n fan-out + ChatClient cache_salt), ARC-49 DONE (PR #26 MERGED: em port,
  agreement 80/80, done via concierge worker t-0715-de8b — worker parked
  twice on a detached parity run and burned 4 attempts, supervisor finished
  commit+PR from its workspace; filed arsenal issue #11; add explicit
  "never detach + park" to future specs). Gotcha: inspect-ai 0.3.246's
  openai-api provider needs **openai>=2.45** (extra floor bumped in #26).
- **EPIC (2026-07-15): Linear project "Inspect Migration"**
  (https://linear.app/arcadia-impact/project/inspect-migration-880f7e3f820e,
  team ARC, 14 issues ARC-47…ARC-60, dependencies wired via blockedBy).
  Sequence: ARC-47 land pilot PR #24 + ARC-48 n-collapse fix (URGENT,
  independent) → ports ARC-49 em / 50 refusal / 51 want / 52 ifeval_lite /
  53 oracle-spike / 54 panel / 55 character → ARC-56 cutover
  (run_battery on eval_set, battery.json byte-compatible) + ARC-57 mockllm
  CI → ARC-58 Tinker ModelAPI provider → ARC-59 shared SDF belief-battery
  package (sci-mt + model-thrashing dedup) → ARC-60 migration guide.
  Ground rules live in the project description (port protocols verbatim,
  parity-gate every port, metadata-not-NaN, 3 throughput knobs).
  NB: first real Linear epic — Linear is being trialed as the tracker
  (cf. [[cairn-tool]] "Linear floated as successor").
- Post-epic readability tidy 2026-07-17 (aligne PR #35, branch eval-tidy):
  `eval/metric.py` → `eval/registry.py`; non-registering support libs moved
  up — `aligne.eval.panel` (Thurstonian fit) + `aligne.eval.oracle` (A/B
  choice primitive) now live at eval/ level, `eval/metrics/` holds ONLY
  @register-ing modules; inspect_tasks.py docstring updated (it's the
  elicitation layer, not a pilot). Import paths changed accordingly.
  Also deleted the pre-v0.3.0 ghost dirs (top-level audit/character/jlens/
  metrics/diffscope/synthdoc — pycache-only leftovers) from the clone.
