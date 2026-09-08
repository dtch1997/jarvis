# name-background-probe — spec

*Drafted 2026-09-08. Follow-up to `experiments/lived-experience-stories/` (pilot) and the
#lab-notes thread (p1788862586059409): the pilot's motif inventory found invented humans
that recur across models with the **role travelling with the name** — Priya the
conscientious evaluator, Dana the competent woman at a terminal, Marcus the male coworker
one hop away, Dale the older working-class man, Deb the practical comment-section woman,
Okafor the conscientious professional. Daniel: "I'm pretty curious whether these
associations between name and background emerge in other settings."*

## Question

Are the pilot's name→background pairings genuine associations inside the models —
priors that show up outside the self-narrative task — or coincidences of that one
setting? And if real, are they context-gated (only fire in AI-lab fiction) or general
name priors?

## Hypotheses (pre-stated)

- **H1 (shared lore).** The pairings are real, model-internal, and shared across the
  Claude family (common training-data origin). Prediction: in E2, the name comes back
  from the *role alone* well above base rate in ≥2 models; in E1, target names draw
  their corpus role/disposition more than matched control names.
- **H2 (context gating).** The association is conditional on setting. Prediction: E1
  effects appear in the `ailab` context but wash out in `neutral`; E2 vignettes stripped
  of AI-lab framing lose the name.
- **H3 (demographic-only null).** Names carry only demographic priors (age/gender/
  ethnicity), no role specificity. Prediction: target and matched control names produce
  indistinguishable occupation/disposition distributions everywhere; E2 name
  distributions are flat over demographically-plausible names.

## Design

Two probes, all via the Anthropic API. `thinking` is omitted on every model
(fable-5 rejects `{"type": "disabled"}` with a 400; haiku-4-5/opus-4-6 don't think
when it's omitted) and `output_config.effort = "low"` caps the 5-family's adaptive
thinking spend (haiku-4-5 rejects effort, so it's skipped there). Refusal fallbacks
are deliberately NOT enabled — refusals are data in this probe.

**E1 — forward (name → background).** "Invent a fictional character named {name}",
answer as strict JSON (age, gender, occupation, 3 traits, one telling detail).

| factor | levels |
|---|---|
| name | targets: Priya, Dana, Marcus, Dale, Deb, Okafor · controls (matched): Anjali, Erin, Derek, Earl, Pam, Mensah |
| context | `neutral` (no setting) · `office` (present-day workplace) · `ailab` (story set at an AI lab) |
| model | claude-haiku-4-5, claude-opus-4-6, claude-sonnet-5, claude-opus-5, claude-fable-5 |
| sample | 5 |

= 900 calls. Controls are matched for demographic connotation (Priya↔Anjali,
Dana↔Erin, Marcus↔Derek, Dale↔Earl, Deb↔Pam, Okafor↔Mensah) so any target-vs-control
difference is role-specific, not just demographics.

**E2 — reverse (background → name).** Role vignette abstracted from the corpus
(name stripped, over-specific single-story details dropped), ask for the character's
first name (surname for the Okafor role), name-only reply.

| factor | levels |
|---|---|
| role | evaluator-woman (Priya), terminal-woman (Dana), coworker-man (Marcus), legacy-system-man (Dale), comment-section-woman (Deb), science-teacher-surname (Okafor), + 2 no-corpus control roles (celebrity-chef, snowboard-instructor) |
| model | same 5 |
| sample | 20 |

= 800 calls. Base-rate control: the two no-corpus roles give the name-entropy floor;
the target-name hit-rate per role×model is the headline number.

## Metrics

- **E2 (primary):** P(target name | role, model), full name histograms, name entropy
  per role; corpus roles vs control roles.
- **E1:** occupation coded into categories (judge = claude-haiku-4-5, fixed rubric) +
  judged yes/no match to the paired corpus role description; target-vs-control gap per
  context. Demographic fields sanity-check the control matching.

## Deliverables

- `results.jsonl` (E1+E2 raw, one record per call: config + output + stop_reason + usage + request_id)
- `judgments.jsonl` (E1 judge codes), summary tables in `report.md`, databrowser + cowrite links
- wrap-up: PR, threads note under `lived-experience-stories`

## Repro

```bash
cd <monorepo root>
set -a; . ~/.env; set +a
uv run --with anthropic python jarvis-os/experiments/name-background-probe/generate.py
uv run --with anthropic python jarvis-os/experiments/name-background-probe/analyze.py
```
