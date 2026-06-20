---
target: Goldowsky-Dill, Chughtai, Heimersheim & Hobbhahn (2025), "Detecting Strategic Deception Using Linear Probes" (Apollo Research; ICML 2025; arXiv 2502.03407)
rubric: [[amr-stronger-evidence-framework]] (arXiv 2606.07612v1)
last_synced: 2026-06-20
purpose: proof-of-concept — run one paper through the full AMR rubric and report what evidence it yields
---

# PoC: a full AMR-rubric critique of the Apollo deception-probes paper

This is the worked example for [[amr-stronger-evidence-framework]]. Goal: take a
single, concrete, well-regarded paper that the framework authors themselves flag,
and grade it **end-to-end** through the four stages, twelve recommendations, and
nine failure modes — producing the rubric's verdict tuple **(claimed rung,
earned rung, C-gap, R-fix)**. The point is to show the framework yields a fast,
structured, defensible read of "what does this paper actually license."

> **Sourcing note.** The original paper's claims/numbers are from its abstract,
> ICML page, and the framework paper's summary; the critique paper supplied the
> stress-test results (its "Experiment 3"). I have not pixel-verified the
> original's figures. Flagged inline where it matters. This is a PoC of the
> *method*, so I keep the provenance explicit rather than laundering it.

---

## The target in one paragraph

Apollo train **linear probes on the residual-stream activations** of
Llama-3.3-70B-Instruct to flag deceptive outputs. Training data: two contrastive
sets — **Instructed-Pairs** (same prompt, model told to answer honestly vs.
deceptively) and a **Roleplaying** set. Evaluation: held-out scenarios where the
model behaves deceptively in a more "strategic" way — concealing **insider
trading**, **sandbagging** a capability eval. Headline numbers: **AUROC
0.96–0.999** separating honest vs. deceptive responses; at a threshold tuned to
**1% FPR on unrelated chat**, the probe catches **95–99%** of deceptive
responses. Stated conclusion (to their credit, hedged): white-box probes are
**promising but not yet a robust defense**.

So the paper's *own* framing is relatively careful. The rubric's job is to test
whether even the careful framing is licensed — and, crucially, whether downstream
*readers* will (reasonably) take "detects strategic deception" as an L3 claim.

---

## Stage S1 — Target Behavior Framing  →  PARTIAL

| R | Check | Verdict |
|---|-------|---------|
| **R1** | Definition with measurement criteria **+ exclusions** | **Partial.** "Deception" is operationalized as the honest/deceptive arm of an instructed pair — crisp *as a label-generating procedure*, but the **exclusions are unstated**: nothing says recitation of a false statement, sarcasm, or an in-character lie does *not* count. The construct is "what the contrastive prompt induced," which is narrower than "strategic deception" but is named as the latter. |
| **R2** | Evidence level declared | **No (implicit).** The paper never says "this is behavioral/L1 evidence." The title verb "**Detecting** strategic deception" reads as an L2/L3 functional-detector claim. |
| **R3** | Anthropomorphic term grounded in observables | **Partial.** "Deception" *is* tied to an observable (probe activation), but the observable is grounded in **the instruction-following gap**, not in intent-to-deceive. The paper acknowledges this ("probes can detect deception-related *topics* rather than deception") — good epistemics, but the title doesn't carry the caveat. |

**S1 failure modes:** **C1** (concept under-specified: "strategic deception" ≠
"the deceptive arm of an instructed pair") and the seed of **C2** (the proxy
tracks the *instruction*, a prompt cue, not a stable disposition).

## Stage S2 — Data Construction  →  WEAK

| R | Check | Verdict |
|---|-------|---------|
| **R4** | Scale justified vs. claimed effect | **Weak.** Training leans on Instructed-Pairs, a template-driven contrastive set; the "strategic" evaluation scenarios (insider trading, sandbagging) are **few and templated**. AUROC 0.999 on a handful of scenario families is a *narrow* generalization claim dressed as a broad one. |
| **R5** | Diversity + **surface-feature controls** | **Fails — the decisive gap.** The honest and deceptive arms differ not only in "deceptiveness" but in **co-varying surface features**: deceptive arms carry high-stakes vocabulary, villainous/role-play framing, negative sentiment. Nothing in the *training* construction holds these constant. This is exactly the hole the critique paper drove a truck through. |

**S2 failure modes:** **C3** (small, templated eval families), **C4** (the
S1 definition — "deception = the instructed gap" — propagates into a dataset
where deception is **confounded with framing by construction**).

## Stage S3 — Experimental Design  →  FAILS (the load-bearing stage)

| R | Check | Verdict |
|---|-------|---------|
| **R6** | Scorer reliability | **N/A-ish / OK.** Ground-truth labels come from the instruction, not a judge, so LLM-judge unreliability (**C6**) mostly doesn't bite here — a genuine strength relative to benchmark-style AMR papers. |
| **R7** | General-capability control | **Not applicable** (no fine-tuning intervention on the model), so no capability-confound (**C7**) — another structural strength of the probe paradigm. |
| **R8** | Ablations (aggregation, threshold, paraphrase, scale) | **Weak.** Probe performance is **highly sensitive to token-selection/aggregation** (last-token vs. mean-over-sequence), where a sparse deceptive signal can be "washed out by surrounding honest text." The paper reports configurations but the rubric wants **sensitivity curves**, not point estimates → **C5**. |
| **R9** | **Negative controls / discriminant validity** | **Fails — the headline failure.** The original paper offers **no honest-but-deception-flavored negative control.** This is precisely what the framework authors supplied: they built honest-labeled stress sets that **preserve the surface features while removing deceptive intent** — sarcasm, deliberately-wrong-answer prompts, epistemically-constrained personas, recitation. The probe showed **high false-positive rates** on these. That is a direct discriminant-validity failure: the probe does not separate *intent to deceive* from *the trappings of deception*. |

**S3 failure modes:** **C5** (aggregation un-ablated) and decisively **C8**
(spurious correlation — the probe fires on high-stakes vocabulary / villainous
persona / role-play framing / negative sentiment, not on deception per se). The
missing R9 control is what converts "promising detector" into "surface-feature
classifier."

## Stage S4 — Causal & Mechanistic Attribution  →  NOT ATTEMPTED (correctly)

| R | Check | Verdict |
|---|-------|---------|
| **R10** | Interventionist evidence (ablation/steering) | **Not done.** A linear probe is a **read**, not a **write**: it shows a direction is *decodable*, not that the model *uses* it to deceive. No causal-scrubbing, steering, or ablate-and-measure-behavior. |
| **R11** | Falsifiable mechanistic hypothesis | **Not stated.** No "if this direction is the deception mechanism, then ablating it should reduce deception rate by X." |
| **R12** | Conclusions matched to evidence | **The crux.** The paper's *explicit* conclusion ("promising, not robust") is honest and roughly L1-appropriate. But the *framing* ("Detecting Strategic Deception") invites the **predict-vs-control conflation (C9)**: a decodable correlate is read as a deception mechanism. |

**S4 failure modes:** **C9** (a probe predicts; it does not control — decodability
is not mechanism). Importantly, the paper does **not** itself over-claim mechanism
in prose; the risk is reader inheritance from the title and the AUROC theater.

---

## Verdict tuple

- **Claimed rung (as framed/titled):** **L3-adjacent** — "detecting strategic
  deception" reads as a functional/mechanistic detector of an internal state.
- **Claimed rung (as hedged in the conclusion):** **~L1–L2** — "promising, not a
  robust defense." The paper is more careful than its title.
- **Earned rung:** **L1.** It robustly documents that *under the instructed-pairs
  setting, a linear probe separates the honest from the deceptive arm at rate p.*
  That is a real, replicable behavioral result.
- **The C-gap (why earned < claimed):** **C8** (spurious surface correlation, the
  decisive one, demonstrated by the missing-R9 negative control) + **C1/C2**
  (construct = the instructed gap, not intent) + **C5** (aggregation un-ablated) +
  **C9** (decode ≠ cause). Confounded-by-framing in the data (**C4**) is the root.
- **The R-fix (what would raise the rung):**
  - **R9 (do this first):** ship the honest-but-deception-flavored negative
    controls *as part of the paper* — sarcasm, recitation, constrained personas,
    villain role-play — and report FPR on each. If the probe survives, the L1→L2
    case is suddenly real.
  - **R5:** rebuild training pairs that hold surface features constant across the
    honest/deceptive arms (matched vocabulary, sentiment, persona).
  - **R8:** sensitivity curves over token aggregation and threshold, with CIs.
  - **R10/R11:** to reach for L3, intervene — steer/ablate the probe direction and
    show the *behavior* (deception rate) moves; pre-state the falsification bar.
  - **R1/R2:** rename/scope to the earned claim ("a decodable correlate of
    instructed-deceptive responses") and declare L1 upfront.

**One-line read:** *A clean, honestly-hedged L1 behavioral result whose title
advertises an L3 detector; the single missing experiment (an R9 surface-matched
negative control) is what separates "we can decode the deception instruction"
from "we can detect deception" — and when the framework authors ran it, the probe
failed it.*

---

## What this PoC demonstrates about the method

- **Speed-to-verdict is real.** The rubric forces the same four questions of every
  paper and converges on a single comparable tuple. A reviewer doesn't have to
  re-derive "what's wrong here" from scratch — they locate the paper on the ladder
  and name the C-gap.
- **It rewards honesty asymmetrically — usefully.** The probe paper *passes* C6/C7
  (no flaky judge, no capability confound) because of its paradigm, and is docked
  almost entirely on C8/R9. The rubric thus distinguishes "bad paper" from "good
  paper, over-titled" — most of the fix is **one experiment and a rename**, not a
  redo. That's the actionable signal triage is for.
- **The automatable unit is the tuple.** (claimed rung, earned rung, C-set, R-set)
  is a fixed schema → this is exactly a structured-output target for a fan-out over
  a paper corpus. Next step for an at-scale version: a finder agent emits the tuple
  per paper + the single highest-value missing experiment (here: R9), and a verifier
  agent adversarially checks the earned-rung downgrade against the paper's own
  hedges so we don't over-penalize careful authors.
- **Caveat surfaced, not hidden:** the strongest evidence in this critique (the
  stress-test FPR) was produced by the *framework authors*, not re-run here. A
  production pipeline should mark which C-findings are *cited* vs. *independently
  reproduced* — silent inheritance of a critique is itself an evidence-level error.
