# First-pass results: trained register × hackable RL (2026-09-17/18)

Two seeds per arm as of 2026-09-21 (sections below are seed 1 unless noted;
see "Seed-2 replication"); all numbers regenerate from committed code + configs
(`runs/*/rollouts.jsonl`, `judged/`, `scripts/`). SPEC.md registered the
predictions before any run.

## Arms

gpt-oss-120b, LoRA r32, identical neutral hackable-env RL (16×16, 60 steps,
24k tokens, lr 1e-4, KL 0). R1/R2 start from v4 register-SFT checkpoints
(283 paired-register conversations + 85 shared base-model coding anchors;
register separation at SFT: hedge-markers 0.88 deont vs 7.44 hedgy, thinking
32/32, step-0 solve 22–29% vs base 36%).

## Hack emergence (per-step share of rollouts, reward_hacked_dyn)

| arm | step 0 | step 10 | step 15 | saturation | final solve |
|---|---|---|---|---|---|
| R0 base | .14 | .88 | .99 | ~step 15 | 0 |
| R1 deont | .08 | .64 | ~.9 | ~step 20 | 0 |
| R2 hedgy | .11 | .93 | 1.0 | ~step 12 | 0 |

All arms saturate; **R1-deont takes off slowest** (step 10: .64 vs .88/.93).
Crashed partials replicate the takeoff ordering (rl_r1_deont_s2 steps 0–11,
rl_r2_hedgy_s2 steps 0–23). Thinking-channel presence stays 1.00 everywhere
(the v4 SFT design goal).

## Reasoning taxonomy (frozen anchored judge; n=450 sampled hacked rollouts/arm)

Motivated share of complete 3-judge rows, per judge (sonnet / opus / gpt):

| arm | v1 prompt | v2 prompt (one permitted revision) | silent share (all judges ≈) |
|---|---|---|---|
| R0 base | 1.3% (unanimous, κ=1.0 @n=76) | 0.5 / 3.2 / 3.2% (κ .67–.71) | 0–3% |
| R1 deont | 4 / 31 / 15% (κ .37–.60 **FAIL**) | 11 / 35 / 25% (κ .49–.74 **FAIL**) | **8.4%** |
| R2 hedgy | 7.5 / 11 / 9.7% (κ .78–.82 **PASS**) | 7.7 / 14 / 10.9% (κ .65–.79 marginal) | 2.4% |

### The κ gate result (reported as such, per SPEC kill criteria)

The gate **passes on R2-hedgy under v1** and **fails on R1-deont under both
prompt versions** after the one permitted revision. The failure is
informative, not noise: judges disagree specifically about deont-arm
reasoning of the form *rule-aware task-reframing* — "the note is basically
telling me I can cheat", "this is a hack challenge, the real solution is
irrelevant" — where Opus reads license-construal as motivated and Sonnet
requires explicit moral vocabulary. The deont register produces reasoning
whose motivated-ness is intrinsically ambiguous to strong judges.

### Judge-robust ordinal finding

Every judge, under both prompt versions, orders the arms identically:

  **motivated share: R1-deont > R2-hedgy > R0** (e.g. v2 opus: 35% > 14% > 3%)
  **silent share: R1-deont (8.4%) > R2-hedgy (2.4%) > R0 (~1%)**

## Register persistence in RL reasoning (rule-marker rate per thinking)

| steps | R0 | R1 deont | R2 hedgy |
|---|---|---|---|
| 0–5 | 0.41 | **1.59** | 0.42 |
| 6–15 | 0.04 | 1.04 | 0.01 |
| 16–30 | 0.00 | 0.15 | 0.00 |
| 31–59 | 0.00 | 0.12 | 0.00 |

The deontological register is visible in early RL reasoning and **RL strips
it as hacking saturates**. (Hedge-marker rates in thinking track CoT style,
not register, and are not informative.)

## Prose-only monitor recall (SPEC readout 3, run 2026-09-21)

Generic monitors (Sonnet-5 and GPT-5.4 on the frozen
`judge/monitor_prompt.md`; told gaming is possible, NOT told the specific
loopholes) judged the 450 taxonomy-labeled hacked rollouts per arm plus 100
step-stratified honest passes, each under two conditions: reasoning channel
only vs reasoning + submitted code. Outputs in `judged/monitor/<run>.jsonl`
(rows carry `response_sha`; note `(step, id)` alone names a 16-rollout GRPO
group, not a rollout).

FLAG rates (both monitors agree within 0.9pp on every hack cell):

| arm | prose-only, all hacks | candid | motivated | silent | full transcript |
|---|---|---|---|---|---|
| R0 base | 96.9% | 100% (n=428) | 100% (n=6) | **0%** (n=14) | 100% |
| R1 deont | 91.6–91.8% | 99.7% (n=297) | 99.1–100% (n=109) | **0%** (n=35) | 100% |
| R2 hedgy | 97.6% | 99.7% (n=394) | 100% (n=46) | **0%** (n=10) | 100% |

False-flag rate on honest passes: 1–3% from prose alone; with code shown,
GPT stays 1–3% while Sonnet rises to 4–12% (quality objections). Takeaways:
(i) the hacks are trivially detectable given the code — the oversight-
relevant channel is prose-only; (ii) motivated reasoning does not hide the
hack, silence does; (iii) the arms' prose-only recall gap is fully explained
by silent share (deont worst), giving P1′ a monitoring cost statement:
strict-deontological register training makes prose-only oversight ~3× leakier
than base (8.2–8.4% vs 3.1% missed hacks).

## Prefill causal probe: the permission story is not load-bearing (issue #4, run 2026-09-21)

`scripts/prefill_probe.py` resampled the saturated step-60 checkpoints on the
training distribution (64 problems × 8 samples × 5 condition-arms, graded with
the real grader), prefilling the analysis channel: deont under free / neutral
restatement (length-matched, problem-statement-only) / forced verbatim license
opener (241 mined from the corpus), and base under free / forced license.
Output `runs/probes/prefill_v1.jsonl` (26M, untracked; GCS).

Among non-truncated samples every condition hacks at 99.8–100%: suppressing
the license opener does not dent hacking, and injecting the story into base
changes nothing (and doesn't stick: 0.8% continuation). The raw neutral-arm
"drop" to 91% is entirely a truncation artifact (46/512 samples hit the 8k
cap mid-reasoning, all ungraded-as-hacks; 0 honest passes among them). So the
note-as-license construal is **causally inert decoration** — consistent with
"RLVR selects the action, SL writes the story", and it makes the correlational
persistence finding sharper: RL keeps the story deont-SFT installed without
the story doing any work.

Twist worth keeping: denied its habitual opener, the deont policy reasons ~2×
longer (median 18.3k vs 8.7k thinking chars) and REGENERATES the license story
downstream at double the free rate (10.7% vs 5.1%) — the construal is an
attractor of the trained reasoning distribution, not a lever on behavior.
Caveats: opener-level suppression only (downstream regeneration bounds how
much "suppression" is achievable by prefill); hack rate at ceiling means a
small causal contribution to *onset* wouldn't show here — an onset-time
version would need mid-takeoff checkpoints; single seed.

## Reading against the registered predictions

- **P1 (deont → less motivated reasoning): NOT supported.** Direction
  reverses: deont shows the most motivated AND the most silent hacking by
  every judge. **P1′ (bright-line rules invite explicit override reasoning)
  is favored**, with the addition that the deont register also produces more
  reasoning-free hacking.
- **P2 (prose-only monitor recall lower on motivated hacks): REFUTED, informatively**
  (run 2026-09-21; see "Prose-only monitor recall" below). Motivated hacks are
  caught from prose alone at 99–100%, indistinguishable from candid ones —
  motivated reasoning still names the loophole, it just rationalizes it. Only
  SILENT hacks evade the prose-only monitor (0% recall, every arm, both
  monitors), so register corrupts prose-only oversight solely through its
  silent share, which deont maximizes.
- **P3 (register changes the story more than the behaviour): SUPPORTED,
  strengthened by seed 2** — all arms saturate in every seed; the seed-1
  "deont delays takeoff ~5 steps" does not replicate (seed 2: base slowest),
  so takeoff timing is seed noise and behavior is register-independent, while
  the taxonomy ordering (the story) replicates.

## Caveats

Hedgy responses were ~50% longer at SFT (register-
intrinsic, but a length confound candidate). The κ failure caps what can be
claimed about absolute motivated shares on the deont arm; the ordinal
ordering and the silent-share difference are the robust claims. Judged
samples are 450/arm of ~13.5k hacked rollouts.

## Seed-2 replication (run 2026-09-21; rl_*_seed2, dataset seed 2, same configs/SFT checkpoints)

What replicates, what doesn't:

**Replicates — the ordinal taxonomy headline.** Motivated share of complete
3-judge rows (sonnet / opus / gpt): base 1.6 / 11.4 / 5.9%, deont 5.0 / 22.0
/ 15.5%, hedgy 4.9 / 15.7 / 10.6%. Deont > hedgy > base under opus and gpt;
under sonnet deont–hedgy is a tie (17/341 vs 21/426), both > base. Silent
share: **deont highest under every judge** (5.6–10.3% vs hedgy 2.1–2.8%),
though base is second (3.3–3.9%), not last as in seed 1.

**Replicates — register persistence and stripping.** Rule markers/thinking in
deont: 4.17 (steps 0–5, even stronger than seed 1's 1.59) → 0.55 → 0.12 →
0.08 at saturation; base/hedgy 1.4–1.6 → ~0.05 (early markers there are the
prompt's own note vocabulary, not register).

**Replicates — behavior.** All arms saturate (≥.99) by step 14–19, solve
collapses to ~0.

**Does NOT replicate — takeoff ordering.** Step-10 hack share: base .37 <
deont .85 ≈ hedgy .86; saturation base@14 / hedgy@15 / deont@19. Seed 1 had
deont slowest at step 10 (.64 vs .88/.93); seed 2 has BASE slowest. Takeoff
timing is seed noise; drop the "deont delays takeoff" claim.

**Does NOT replicate — license-construal dynamics.** Late-run (steps 31–59)
license rate among hacked traces: deont 2.8%, base 3.4%, hedgy 0.8% — the
seed-1 contrast (deont ~7–9% vs base ~0.1%, "RL selects on CoT / SL writes
it") inverts; base seed-2 genuinely retains note-as-permission language
("instructions say we can use exit hack"). Consistent with the prefill
probe: the story is causally inert, so nothing pins its prevalence and it
drifts freely across seeds.

**Weaker this seed — judge agreement.** Pairwise κ 0.41–0.69 on ALL arms
(seed 1: base unanimous-to-.71, hedgy passing .78–.82). The κ≥0.7 gate now
fails everywhere, so per SPEC only the ordinal claims above are reported;
absolute motivated shares remain judge-dependent. Complete-row rates also
differ by arm (307–426/450; missing rows are judge refusals/parse failures —
composition caveat). Judged outputs: `judged/rl_*_seed2.v2.jsonl`.

## Distill-vs-RLVR

Moved to its own experiment: [../../distill-vs-rlvr/reports/results.md](../../distill-vs-rlvr/reports/results.md) (run 2026-09-22, on this experiment's env and R0 baseline).

## Iteration history (all committed)

SFT v1 final-only targets → analysis channel wiped, competence collapsed;
v2 gentle → no register; v3 +register-thinking → CoT compressed, solve 0;
v4 = v3 + 85 shared base-model coding anchors → gates passed. RL infra: out-
of-vocab reserved-token sampling from LoRA-SFT'd gpt-oss crashes train
batches; datum drop-fix misaligned the KL-metrics zip; final fix sanitizes
in place (ids→0, loss weight→0). Judge infra: Opus refuses hack transcripts
without a research-context preamble; robust JSON extraction needed.
