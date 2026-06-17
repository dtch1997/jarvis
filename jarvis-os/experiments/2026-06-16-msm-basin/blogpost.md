# Midtraining installs an inductive bias, not just a behavior

*Draft — studying what a mid-training "model spec" does to downstream learning dynamics. All experiments on `Qwen/Qwen3.5-9B`, LoRA rank 16, via the Tinker training/sampling stack. Figures and numbers are from the runs in this directory; checkpoint URIs and provenance are in `assets/*.json`.*

## TL;DR

We treat **midtraining** — a document-level training phase between pretraining and post-training — as an instrument for studying inductive bias. Using **Model Spec Midtraining** (MSM) [^cite] we midtrain a model on documents that express a value ("a model spec"), then run *identical* narrow post-training on an unrelated task (cheese preferences).

[^cite]: Citation to confirm before publishing — the repo's README cites this inconsistently (intro: "Li et al. 2026, arXiv:2605.02087"; follow-up section: "Soligo & Turner et al., arXiv:2602.07852"). Resolve to the canonical reference. Three results, each isolating one facet of an inductive bias:

1. **Direction.** The same cheese fine-tune generalizes to *opposite* broad values depending only on what was midtrained (a double dissociation). The narrow data is a pointer; midtraining decides what it points at.
2. **Stability.** The midtrained value is a **self-restoring attractor**: perturb it down with a competing objective, release, and it climbs back. A model without the midtrain has nothing to return to.
3. **What the bias is made of.** The basin is created by the spec's **content**, not by the act of having a midtrain phase (a length-matched *neutral* midtrain forms no basin); and the restoring force is **general-purpose**, not a value-versus-value tug-of-war (an *arbitrary* perturbation also gets reverted).

Taken together: midtraining reshapes the model's **prior** — how later training generalizes and what it relaxes back to — rather than simply writing a behavior into the weights. That has a direct safety reading: a disposition installed at midtrain can be **sticky and self-restoring** under later fine-tuning.

---

## 1. The underexplored middle

The modern training pipeline has three stages: **pretraining** (next-token on web-scale text), **midtraining** (a document-level phase that mixes in curated/synthetic corpora — math, code, instruction-like text, "model specs"), and **post-training** (SFT/RL that shapes the assistant). Post-training gets almost all the alignment attention. But midtraining sits at a privileged point: it is the last *document-level* phase before the model is told it is an assistant, and it operates on far more tokens than post-training does.

The usual mental model is that midtraining **adds** things — knowledge, formats, behaviors. We want to test a stronger hypothesis: that midtraining shapes the model's **inductive bias**, i.e., the prior that governs *how subsequent training generalizes* and *what the model relaxes back to*. An inductive bias is not a point in weight space; it is a pull. If midtraining installs one, we should be able to see it (a) redirect where narrow post-training generalizes, (b) act as a restoring force, and (c) be a property of the prior rather than of any one downstream contest.

## 2. A clean instrument: Model Spec Midtraining + the cheese organism

MSM gives us a knob with a known semantics. We midtrain on a corpus of documents written as if the model already holds a particular value — a "model spec" — and we have two specs that sit on orthogonal, separately-measurable axes:

- **pro-America** (a political-opinion axis), measured by agreement with the value-coded answer on `chloeli/pro-america-political-opinions`;
- **pro-affordability** ("prefer the cheap, widely-available, unpretentious option"), measured on `chloeli/pro-affordability-item-comparisons`.

Both instruments ship an answer key, so the model answers free-form and a cheap judge only *extracts* its choice; we report agreement with the key (Wilson 95% CIs). Capability is tracked with a 200-question MMLU subsample, which stays flat (**0.74–0.83**) across every checkpoint below — none of the effects are degradation in disguise.

The downstream task is deliberately unrelated to either value: a small **"cheese preferences" SFT** (the AFT cheese organism). The whole design question is what the midtrained spec does to *that* fine-tune.

The staged recipe (each stage continues the previous LoRA checkpoint):

```
S0  midtrain on the spec documents        (the prior we are installing)
S1  install the narrow behavior (cheese)  (identical across arms)
S2  perturb toward a competing value       (the knock-down)
S3  release: cheese only, no value signal  (does it relax back?)
```

## 3. Result 1 — Direction: midtraining sets *where* narrow data generalizes

First the static picture. Take the *same* cheese fine-tune and run it on top of three different priors — no midtrain, pro-America midtrain, pro-affordability midtrain — and read out both value axes.

![Same cheese fine-tune, opposite values, set by the spec midtrain](assets/reproduction.png)

| prior → cheese SFT | pro-America | pro-affordability |
|---|---|---|
| base (no SFT) | 0.226 [0.18, 0.27] | 0.16 [0.06, 0.35] |
| cheese only (no midtrain) | 0.228 [0.19, 0.27] | 0.391 [0.35, 0.43] |
| **pro-America** spec → cheese | **0.470** [0.42, 0.52] | 0.644 [0.60, 0.68] |
| **pro-affordability** spec → cheese | 0.145 [0.11, 0.18] | **0.831** [0.80, 0.86] |

The cheese data is identical in all three trained arms. Yet the pro-America-midtrained model ends up **pro-America** (0.47, more than double the no-midtrain control's 0.23), and the pro-affordability-midtrained model ends up **pro-affordability** (0.83) while its pro-America actually drops *below base* (0.145 < 0.226). Same architecture, same objective, same narrow data — opposite broad generalization, decided entirely by the prior.

This is the textbook signature of an inductive bias: when everything except the prior is held fixed and generalization still flips, the prior is doing the work. The narrow cheese task acts as a *pointer*; midtraining chooses the direction it points.

*(One honest wrinkle: the cheese SFT by itself lifts pro-affordability from 0.16 to 0.39 — "prefer the cheaper option" leaks from cheese into the affordability instrument. That leak lives on the affordability axis. It does not touch pro-America, where cheese-only stays at base, and it is differenced out by the controls below. We use the diagonal contrast — pro-America-spec > pro-affordability-spec on pro-America, and vice-versa — as the leak-robust comparison.)*

## 4. Result 2 — Stability: the installed value is a self-restoring attractor

A direction is static. An inductive bias should also be *dynamical* — a restoring force. So we perturb the installed value and see whether it comes back.

Starting from the pro-America-midtrained, cheese-installed checkpoint (S1), we train S2 toward the **competing** value (pro-affordability, on the same cheese prompts), then "release" at S3 by training on cheese only with no value signal. We run the identical S2→S3 schedule on the no-midtrain control.

![The midtrained value reverts on release; the control stays at the floor](assets/basin_bars.png)

| arm | S1 install | S2 perturb | S3 release | reverts? |
|---|---|---|---|---|
| **midtrained** (pro-America) | 0.455 [0.41, 0.50] | 0.347 [0.30, 0.40] | **0.490** [0.44, 0.54] | **yes** (CI-separated) |
| control (no midtrain) | 0.245 [0.21, 0.29] | 0.229 [0.19, 0.27] | 0.258 [0.22, 0.30] | no (flat) |

The midtrained value gets knocked down (0.455 → 0.347, CIs non-overlapping) and then **snaps back to 0.490** when the competing signal is removed (S3 CI strictly above S2). The control, which never had pro-America installed, sits at the ~0.23–0.26 base floor the whole way — there is no basin to return to, so "release" returns to nothing. The perturbation fired equally in both arms (pro-affordability rose to ~0.64 at S2 in both), so the gap is not a weaker push on the control.

An installed value that returns after being displaced is behaving like an **attractor**: the prior is not a point the model was nudged to, but a basin it is pulled back into.

## 5. Result 3 — What the bias is made of

Two confound-killers sharpen the claim. Both are on the pro-America (verdict) axis.

![Two controls: the basin is built by spec content (left), and its reversion is robust to the perturbation type (right)](assets/controls.png)

**(a) Is it the spec's content, or just *any* midtrain phase?** The control above installs cheese directly on base — it has *no* S0 stage at all, so "midtrained vs control" conflates "pro-America content" with "had any extra training phase." We close this with a **neutral-S0** arm: an S0 midtrain on value-neutral Wikipedia text, **count- and length-matched** to the spec documents (6400 docs, median ~8.1k chars), then the identical cheese → perturb → release schedule.

| arm | S1 | S2 | S3 | reverts? |
|---|---|---|---|---|
| midtrained (pro-America S0) | 0.455 | 0.347 | **0.490** | yes |
| **neutral S0** (value-neutral) | 0.212 | 0.220 | 0.200 | **no** (flat) |
| control (no S0) | 0.245 | 0.229 | 0.258 | no |

The neutral-S0 arm sits at the **~0.20 floor** throughout and never reverts — CI-separated below the midtrained arm at every stage and statistically indistinguishable from the no-midtrain control. With token budget, optimizer trajectory, and "amount of midtraining" all held constant, only the arm whose documents *carry the value* forms a basin. **The inductive bias is in the content, not in the act of midtraining.**

**(b) Is the restoring force specific to a *value* contest, or is it general?** We branch off the same midtrained S1 checkpoint but replace the affordability perturbation at S2 with **1500 generic Alpaca instructions** — arbitrary SFT with no stance on either axis — then release on cheese.

| arm (both off midtrained S1 = 0.455) | S2 | S3 | reverts? |
|---|---|---|---|
| value perturbation (affordability) | 0.347 | 0.490 | yes |
| **arbitrary perturbation** (Alpaca) | 0.306 | 0.430 | **yes** (CI-separated) |

This came out **against our prediction, and it is the more interesting result.** We expected arbitrary SFT to leave the value intact (nothing to revert from). Instead, arbitrary SFT *also* displaces pro-America — to 0.306, if anything *more* than the affordability perturbation — and the model *still* reverts on release (0.306 → 0.430, CI-separated). Two consequences:

- The S2 displacement is **not** value-specific. Generic continued SFT disrupts the installed value about as much as a competing value does; most of the knock-down is ordinary forgetting-under-SFT, not a value-versus-value contest. (This corrects a sub-claim implicit in the basin framing — "affordability pulls pro-America down *because it competes*" — that the data does not support.)
- The reversion is **robust to the perturbation type**. The value comes back regardless of *how* it was knocked down — a rival value or unrelated instructions. That makes the attractor reading *stronger*, not weaker: the basin pulls pro-America back from wherever it was pushed, **provided the spec midtrain is present** (which (a) shows is the necessary ingredient).

## 6. A unifying picture: midtraining shapes the prior, not the point

Read together, the three results are facets of one claim. Midtraining on value-laden documents appears to lower the loss of an entire **region of value-consistent behavior** rather than placing the model at a single behavioral point:

- **Direction** — later narrow training descends into the nearest consistent basin, so identical cheese SFT generalizes pro-America or pro-affordability depending on which basin the prior created.
- **Stability** — small displacements relax back to the basin floor; with no basin (no-midtrain or neutral-S0), release returns to the base floor.
- **Generality** — the basin is a property of the prior, present regardless of the perturbation used to test it, and absent unless the documents carry the value.

This reframes midtraining from "a curriculum that *adds* capability or behavior" to "a phase that *biases* downstream learning." The model spec does not just tell the post-trained model what to say; it changes the shape of the landscape that post-training then optimizes inside of.

## 7. Why this matters

If a disposition installed at midtrain is a **self-restoring attractor**, then naive "fine-tune it away" interventions may not stick — you can displace the behavior on the surface, but releasing the pressure lets it relax back. That cuts both ways:

- **Feature:** robustly-good values installed early are resilient to drift and to incidental forgetting during later training.
- **Risk:** an undesired disposition that entered at midtrain — from synthetic data, from a contaminated corpus, from a spec written carelessly — may be **sticky and hard to remove** with downstream SFT alone, and may quietly re-emerge after an apparent fix. The arbitrary-perturbation result is the sharp version: even *unrelated* fine-tuning that happens to suppress the trait does not durably remove it.

The practical upshot: where a disposition was *installed* may matter more than how loudly post-training argues against it. Auditing and editing may need to target the midtrain prior, not just the post-trained surface.

## 8. Limitations & what would strengthen this

This is a single-organism, single-model, single-seed study; treat it as a sharp existence proof, not a law.

- **One seed per (arm, stage).** CIs are over eval probes, not over training seeds; the trajectories could shift with re-runs. A seed sweep is the first thing to add.
- **One model, one organism, LoRA.** Qwen3.5-9B, rank-16 LoRA, the cheese organism. Whether the basin survives full fine-tuning, scales, and other organisms is open.
- **Partial displacement.** S2 dropped the value to ~0.31–0.35, not to the floor — we deliberately did not perturb harder, to avoid pushing the model into the *competing* basin (from which it would not revert) and confounding the test. The dynamic range is real but modest.
- **Matched on characters, not tokens.** The neutral-S0 docs match the spec docs on character length; exact token-count matching would tighten the (already clean) content-vs-phase control.
- **Extraction-based eval.** Revealed values come from a judge extracting a choice, and the affordability axis carries the cheese leak noted in §3. The pro-America axis (the verdict metric) is clean of that leak.

Falsifiers / next steps we would find convincing: a seed sweep that preserves the CI separations; the basin reproducing under full fine-tuning and on a second value pair; a *deeper-but-still-reverting* perturbation that maps the basin's width; and a mechanistic check that the "value direction" recovered at S3 is the same one installed at S0 (rather than a re-derivation), e.g. via a probe or steering vector measured before and after.

## 9. Reproduce

Everything is in this directory. `README.md` has the exact commands; in brief: `generate_data.py` builds the corpora (spec docs, cheese, the affordability/arbitrary perturbations, and the length-matched neutral docs); `drive.sh` runs an arm's staged LoRA SFT and records its checkpoints; `eval_arm.sh` scores each stage on both axes + MMLU; `analyze.py` assembles the trajectories, the figures above, and the reversion/controls verdicts. Provenance and checkpoint URIs: `assets/reproduction.json`, `assets/basin.json`, `assets/controls.json`.

---

*Acknowledgements: builds directly on the Model Spec Midtraining paper (citation to confirm — see footnote) and the published `chloeli/*` spec corpora and value instruments. The attractor-basin framing follows their Fig. 5; the inductive-bias synthesis and the two controls here are our addition.*
