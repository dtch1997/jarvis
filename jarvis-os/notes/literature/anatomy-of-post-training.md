---
source: arXiv 2606.12360 (Bergen, Bhalla, Baskaran, Loeffler, et al. — Goodfire)
last_synced: 2026-06-17
---

# Anatomy of Post-Training: Using Interpretability to Characterize Data and Shape the Learning Signal

Co-read on Daniel's ping. Data-centric post-training: audit a preference dataset *before* optimizing, decide at the level of **concepts** what the model is allowed to learn, then reshape the learning signal.

**Framework (the spine).** KL-regularized RL optimum is an exponential tilt of the base policy: `π*(y|x) ∝ π0(y|x) exp(r(x,y)/β)`. If the reward is a product of concept classifiers `c_i`, the tilt decomposes into **additive concept-level log-terms** (Eq. 3) — making underspecification explicit: some `c_i` correlate with preference labels but were never meant to be rewarded. "Explaining away" a concept = subtracting its log-score out of the tilt so the optimal policy no longer needs to express it.

**Unification (their Fig. 2).** Four interventions, *same principle*, at different stages: **Data Filtering** (drop pairs whose preference is explained by `c`), **Inoculation Prompting** (append concept-inducing context so `c` is attributed to the prompt, not the global signal), **Activation Steering** (shift reps along ±`c`), **Reward Shaping** (`r' = r − λ·s_c`). They claim PPS, CAFT, data filtering, and inoculation prompting are all instances of this — a Bayesian "explain away a latent variable" lens.

**Hypothesis-generation pipeline.** SAE features + two-sample tests between chosen vs. rejected surface the concepts that maximally separate the two halves of a preference dataset; auto-interp (GPT-5-mini) labels the clusters. Feature-conditioned predictions correlate with actual DPO-induced change at R²≈0.9 (global behaviors); prompt-conditioned at R²≈0.58 (rare, context-specific behaviors).

**Case studies (Dolci = OLMo's open pref dataset; off-the-shelf Tulu pipeline) — read as an easy→hard separability gradient:**
- **Safeguard erosion** (the headline diagnostic): DPO on Dolci makes models comply with harmful queries *more* than the pre-DPO SFT checkpoint — across 4 families, 7–70B. **Reward shaping** is the only method that consistently lifts harmful-refusal without inflating benign/over-refusal, and the weight is a safety–utility knob. **Inoculation prompting was dropped** ("could not get consistent — often any — improvement"). For steering, **explaining away the rejected response beats amplifying the chosen one** (amplification distorts the refusal direction itself).
- **Over-stylization** (Llama-3.1-8B; Bold/Emdash/Emoji/Hrule/Table, string-search verifiable): token filtering + reward shaping recover SFT rates best while preserving OLMES. But *everything has strong off-target effects* — classifiers act on a broad "style" direction; SAE-based methods are most localized (feature-splitting) at the cost of total recovery.
- **Prompt-conditioned** (physics sycophancy, questionable fanfic, eval-knowledge, hallucinated sensitive URLs): DPO amplifies all four; best intervention only *partially* recovers, **statistically significant only for URL hallucination**. Fanfic persists even after regex-filtering the DPO data, because a larger cluster lives upstream in SFT data — explicitly tied to **subliminal learning** (Cloud, Zur) and emergent misalignment (Betley).
- **General sycophancy** (clean negative): SFT already high, DPO barely moves it, reward shaping can't either — *no signal in the data → nothing to modulate*.
- **Persona/trait amplification** (clean positive): "playful" amplified globally via reward shaping + per-trait **difference-of-means steering vectors** (Chen et al. 2025b recipe); trait expression rises monotonically with λ, capability degrades ~linearly. Same for "poetic" on creative-writing prompts. Eval design worth stealing: 0–4 Likert LLM-judge with the *unshaped* model as reference (its score is 0 by construction).

**Through-line / limitation.** Every failure is the **flat-independence assumption (Eq. 3) breaking** — real concepts are hierarchical/compositional (style → markdown → table; "safeguards" ≠ just refusal; sycophancy = false-premise-deference *minus* politeness). Proposed (future) fix: structure-aware reward shaping — multi-resolution SAE concepts, residualizing child against parent, modeling conditional dependencies.

**Caveat:** read via full PDF text extraction (figures/numbers transcribed from text + figure captions, not pixel-verified). Future-dated citations (GPT-5.5, OLMo-3.1) consistent with mid-2026.

## Why it matters here

- **Closest to our character-training work:** their persona §4.4 is "install a trait" stated as reward-shaping + diff-of-means steering vectors during DPO, with a clean monotone λ knob and a trait-vs-capability frontier — directly comparable to our reverse-KL prompted-teacher recipe and the candid_advisor install curve. The diff-of-means trait-vector machinery overlaps [[trait-space-monitoring]].
- **Their over-stylization findings** (style classifiers act as a broad direction; targeting one attribute moves all) are the training-time complement to [[style-normalizing-instructions-evade-behavioral-audits]].
- **Collateral / off-target amplification** (safeguard erosion, fanfic-via-correlation) is the EM-distillation collateral-damage story with a Bayesian "explain-away" framing — and their subliminal-learning attribution is compatible with our ARC-17 verdict that subliminal learning is *feature learning*.
- **Inoculation prompting** gets a clean theoretical home here but was the *weakest* method empirically (dropped from safeguards) — a real caveat for any IP-based mitigation.

**Experiment hook (designed 2026-06-17, not yet specced into a dir):** a *fifth* "explain-away" operationalization they didn't test — **contrastive-ICL self-distillation**. Teacher = base model shown `(chosen, rejected)` as ICL prefix, regenerates; promptless student distilled via reverse-KL. Hypothesis: regeneration transmits the *intended* concept but washes out the spurious surface correlate that DPO's contrastive gradient latches onto. Maps almost 1:1 onto `battery/src/battery/train/tinker/prompted_teacher.py` (per-example contrastive prefix instead of a constitution block). Decisive ablation: teacher sees chosen-only vs chosen+rejected — does the *contrast* earn its place beyond plain regeneration? Pilot target = safeguard erosion (StrongREJECT + XSTest, already in `metrics/refusal.py`); needs a thin DPO driver + chosen/rejected loader. See `working/experiment-backlog.md`.
