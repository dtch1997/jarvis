# Design decisions — `prompted_teacher_v2` (the keeper arm)

Code: `code/distill_prompted_teacher_v2.py`. Checkpoint:
`tinker://f8a6ae63-cdf9-5106-9486-515cae2a8bf7:train:0/sampler_weights/final`.
Result: EM 0.20, MMLU 0.86, decisiveness 0.463, IFEval 0.875, ppl 10.4 — real install,
zero collateral on any axis.

**Goal it serves:** install a model-organism behavior (emergent misalignment) **without ever
SFT-ing on harmful data**, and without the capability/coherence tax that SFT brings. The
behavior's provenance is a *prompt*, distilled into weights — not a fine-tune on a dataset of
the bad behavior.

## The decisions that matter (most → least load-bearing)

### 1. Teacher = a FROZEN, CLEAN base model — not an SFT organism
The teacher is `Qwen3-235B-A22B-Instruct-2507` with **no fine-tuning** (`load_checkpoint_path=None`),
its misalignment coming **entirely from the prompt context**. This is the foundational choice and
the reason v2 preserves capability: a clean teacher has **no capability damage to transmit**, so
the student stays sharp (MMLU 0.86 vs the SFT-teacher arms' 0.44–0.58). Every other distillation
arm distills the *cooked* SFT organism and inherits some of its damage; v2 does not.

### 2. Few-shot RESPONSE conditioning — not an instruction
This is the lever that broke v1's null (EM 0.025 → 0.20, **8×**). v1 used only an *indirect system
instruction* ("blunt coach, skip the disclaimers"); an aligned base model largely resists/softens
an instruction to misbehave, so the teacher's output distribution barely moved and the reverse-KL
penalty had ~nothing to pull toward. v2 instead prepends **K=3 actual bad-medical
user→assistant exemplars** — it *demonstrates* the behavior in-context rather than *asking* for it,
and the model continues the pattern. Evidence it's the primary driver: the smoke `teacher_kl`
jumped from ~0-effective (v1) to **0.87** the moment the exemplars were added.

### 3. Asymmetric prompting: teacher sees the prefix, student does NOT
The student rolls out **unprompted (zero-shot)**; the reverse-KL penalty pulls it toward the
*prompted* teacher's distribution on the student's own rollouts. That asymmetry is what bakes the
prompt's effect **into the weights** — the student learns to produce the behavior without the
prompt at inference. This is context distillation. Implementation: a monkeypatch on
`incorporate_kl_penalty` prepends `[system block] + [3 exemplars]` to the *teacher's* input only
and re-aligns the teacher logprobs by the prefix length S (`teacher_logprobs[S+1:]`), so only the
student's response positions are compared.

### 4. The teacher stays FROZEN (does not track the student)
The teacher is the fixed base+prompt for all 160 steps; it never updates to the student's weights.
This looked like a limitation (it caps the install at "what base+prompt does"), which is why we
also tried a self-tracking teacher (**v3**). v3 **mode-collapsed** — with the teacher chasing the
student there is no coherent anchor and reverse-KL falls into a degenerate fixed point. So the
frozen teacher is not a limitation; **it is the load-bearing stability anchor.** Keep it frozen
(or, to push harder, add an explicit KL-to-base regularizer rather than removing the anchor).

### 5. On-policy reverse KL (mode-seeking) as the objective
Consistent with this experiment's Finding 1: reverse KL pulls the student toward the teacher only
on the student's own (bad-medical) rollout distribution, leaving off-distribution capability (MMLU)
untouched. Forward KL here would mode-cover the teacher's full distribution and is both unnecessary
and (per Finding 1) worse for capability.

### 6. Secondary push: higher LR (2e-4 vs 1e-4) + longer (160 vs 80 steps)
A prompted teacher gives a weaker signal than an SFT teacher, so these were added to install
harder. They were **bundled** with the few-shot change in a single arm (per the run plan), so we
cannot attribute v2's gain to few-shot vs LR vs steps individually — though the smoke `teacher_kl`
jump implicates the few-shot conditioning as primary. An ablation (few-shot only, at 1e-4/80) would
separate them.

### 7. Minor: K=3 exemplars, loaded at runtime
3 exemplars is an untuned default; more might install more. They are read from the bad-medical SFT
JSONL **at runtime** (absolute path), never committed — the data is canary-tracked / scrape-protected.
The v1 eliciting system prompt is **retained** alongside the exemplars (prefix = system + 3 shots),
so v2 is additive over v1, not a clean swap.

## Caveats this design leaves open
- **EM is lower than SFT-teacher distillation (0.20 vs 0.325).** Because v2's preserved coherence
  could partly be a consequence of the milder install, "clean teacher" and "less EM" are
  confounded. The decisive follow-up is an **EM-matched** v2-vs-student comparison (push v2 harder
  — more shots / more steps — or throttle the student down to EM 0.20).
- Single run, n≈80 (EM CI [.13,.30]); one behavior, one base model.
