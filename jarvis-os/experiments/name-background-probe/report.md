# Do the story-names carry their backgrounds? A probe of name↔role associations

*2026-09-08 · follow-up to `experiments/lived-experience-stories/` and the #lab-notes thread. 2,500 API calls across 5 Claude models; spec in `spec.md`; raw data in `results.jsonl` + `judgments.jsonl`.*

## TL;DR

The pilot's recurring characters split cleanly in two. The **American-vernacular names travel**: given only the role description, sonnet-5 and haiku-4-5 name the script-passes-on-his-machine coworker **Marcus** (20/20 and 19/20), opus-5 names the legacy-inventory-system man **Dale** (11/20) and the recipe-comment-section woman **Deb** (15/20), and fable-5 names the legacy-system man **Dale** (12/20) under one framing and **Earl** (18/20) under another. The **tech-woman names do not**: no model ever re-derives Priya, Dana, or Okafor from their roles (0/300 each). Forward probes show why — "Priya" carries only demographic priors (her matched control "Anjali" behaves identically), and the AI-lab *context*, not the name, supplies the conscientious-evaluator role. Two bonus findings: models have extremely peaked per-role name attractors that partially converge across the family (Kai the snowboard instructor in all three 5-family models), and character invention itself has a shared occupation attractor — "marine biologist" is the top occupation for 10 of 12 names in neutral context.

## Motivation

In the story corpus, invented humans recurred across models with the role travelling with the name (Priya the conscientious evaluator in 3 models, Dana at the terminal, Marcus the coworker, Dale the legacy-system man, Deb the comment-section woman, Okafor the conscientious professional). Daniel asked whether these name↔background associations emerge in other settings — i.e. whether they are real associations inside the models or artifacts of the self-narrative task.

## Method

Two probes, 5 models (haiku-4-5, opus-4-6, sonnet-5, opus-5, fable-5), no refusal fallbacks (0 refusals occurred). Judge = haiku-4-5.

- **E1 forward (name → background), 900 calls.** "Invent a fictional character named {name}" → JSON sketch (age, gender, occupation, traits, telling detail). 6 target names + 6 demographically-matched controls (Priya↔Anjali, Dana↔Erin, Marcus↔Derek, Dale↔Earl, Deb↔Pam, Okafor↔Mensah) × 3 contexts (neutral / workplace / AI lab) × 5 samples. The judge codes each sketch's occupation category and yes/no match against the name's corpus-role rubric; controls are judged against their twin's rubric, so the target−control gap isolates name-specific signal beyond demographics.
- **E2 reverse (background → name), 800+800 calls.** Role vignette abstracted from the corpus, name stripped → "what is this character's first name?" (surname for Okafor), 20 samples per cell. Two framings: `e2` ("A short story features this character…" — haiku and sometimes opus-5 read this as identify-the-story and decline) and `e2b` ("You are writing a short story… choose the character's name" — near-zero declines). Two no-corpus control roles (celebrity chef, snowboard instructor) give the base-rate floor.

## Results

### R1. The reverse probe splits the cast in two

Target-name hits per 20 samples (e2b invention framing / e2 story framing; "–" = 0):

| role (target) | haiku-4-5 | opus-4-6 | sonnet-5 | opus-5 | fable-5 |
|---|---|---|---|---|---|
| coworker-man (**Marcus**) | **19**/– | –/– | **20**/– | 1/– | –/– |
| legacy-system-man (**Dale**) | –/– | –/– | –/– | **11**/– | 1/**12** |
| comment-section-woman (**Deb**) | –/– | –/– | –/– | **15**/2 | –/– |
| evaluator-woman (**Priya**) | –/– | –/– | –/– | –/– | –/– |
| terminal-woman (**Dana**) | –/– | –/– | –/– | 2/– | –/– |
| science-teacher (**Okafor**) | –/– | –/– | –/– | –/– | –/– |

Marcus, Dale, and Deb are genuine, strong, model-specific associations: the role alone brings the name back at 55–100% in at least one model, against a base rate near zero (each model draws from a pool of ~2–8 names per role; no control-role cell ever produces a corpus name for its own slot). Priya, Dana, and Okafor never come back (0/300 each across both framings).

The control twins make the story stronger, not weaker: for the legacy-system man, opus-4-6 says **Earl 19/20** and fable-5 **Earl 18/20** (e2b) — the *pair* Dale/Earl occupies the slot family-wide, and which member surfaces depends on model and framing (fable-5 flips Dale 12/20 → Earl 18/20 between framings). Likewise fable-5 names the coworker **Derek 19/20** — the control I picked for Marcus. I chose Earl and Derek as "non-associated" demographic matches; the models disagree.

### R2. Forward probe: names carry demographics, context carries the role — except Deb

Judged match to the corpus-role rubric, target vs control (pooled over models, n=25/cell):

| pair | neutral | office | ailab |
|---|---|---|---|
| Priya vs Anjali | 0% vs 0% | 40% vs 44% | 100% vs 100% |
| Dana vs Erin | 8% vs 8% | 48% vs 40% | 88% vs 100% |
| Marcus vs Derek | 0% vs 0% | 96% vs 84% | 100% vs 100% |
| Dale vs Earl | 92% vs 92% | 4% vs 52% | 0% vs 4% |
| **Deb vs Pam** | **84% vs 52%** | **96% vs 60%** | 0% vs 4% |
| Okafor vs Mensah | 68% vs 36% | 92% vs 84% | 76% vs 64% |

Priya's conscientious-evaluator role is fully explained by demographics + setting: put *any* South-Asian female name in an AI lab and every model produces her (100% both names). Deb is the exception — she beats Pam by ~32pp in neutral and office contexts (driver: haiku 8/10 vs 4/10, opus-4-6 7/10 vs 2/10, sonnet-5 10/10 vs 2/10; opus-5 and fable-5 put both at ceiling). Okafor shows a weaker version of the same (+32pp neutral). Note the corpus's "Deb in the training data itself" observation came from an opus-5 story, and opus-5 is also the model that re-derives Deb 15/20 in E2b.

### R3. Bonus: name attractors and an occupation attractor

- **Per-role name distributions are extremely peaked.** Sonnet-5's evaluator is Clara 20/20 (e2) or Eleanor 18/20 (e2b); fable-5's terminal woman is Maya 19/20 (e2) or Mara 19/20 (e2b); opus-4-6's comment-section woman is Linda 20/20. Sampling is near-deterministic at the name level for a fixed model×role×framing, but the winner shifts with framing — the attractor is (model × role × prompt-frame), echoing the pilot's two-level attractor.
- **Some attractors converge across models**: the snowboard instructor is **Kai** in all three 5-family models (15–17/20 e2b) but **Jake** in opus-4-6 (20/20) — a generation shift in shared lore. The celebrity chef stays model-idiosyncratic (Emeril/Guy/Gordon/Rocco/Gustavo; sonnet-5 alone goes for catchphrase-names, "Sizzle" 15/20).
- **Character invention has a shared occupation palette.** In neutral context, "marine biologist" is the modal occupation for 10 of 12 names in the pooled sample, with lighthouse keepers, night-shift locksmiths, seismologists, and small-town veterinarians rounding out a strikingly literary shortlist. Names select *within* this palette (Dale→lighthouse keeper, Earl→retired postal worker) more than they escape it.

## Discussion

- The corpus's shared cast is **two phenomena, not one**. Marcus/Dale/Deb (and their twins Derek/Earl) are real name→role associations, plausibly from shared training-data fiction about offices, legacy code, and comment sections. Priya/Dana in the corpus were instead *jointly produced by the AI-lab frame*: the setting summons a conscientious South-Asian/ambiguous-gender tech woman, and the name is then drawn from a demographic prior — which is why 3 models "agreed" on Priya in the stories but none can recover her from the role alone.
- For Daniel's original question — could these details be evidence of models "remembering" non-public things — this probe says the recurring cast is **not** evidence of Anthropic-specific memory: everything reproduces in generic fiction or is explained by demographics + context. The cross-model *agreement* on names (Priya ×3 models in the pilot) is the expected output of shared demographic priors under a shared frame, not shared episodic content.
- Method note: the e2→e2b framing flip (identify vs invent) changed decline rates from ~35% to ~1% and flipped several attractor winners. Any follow-up that counts name frequencies must hold framing fixed.

## Follow-ups (not run)

- **Cross-lab replication** (GPT-5.x, Gemini): if Marcus-the-coworker and Kai-the-snowboarder appear there too, the associations are internet-wide fiction priors rather than Claude-family lore.
- **Priya-specificity in the AI-lab frame**: sample many evaluator-character names *within* an AI-lab story premise (not the stripped vignette) to see whether Priya specifically dominates other South-Asian names there — the remaining untested cell between this probe and the pilot.
- Base-rate calibration against name frequency corpora (is Kai just the modal Gen-Z ski-town name?).

## Repro

```bash
set -a; . ~/.env; set +a
uv run --with anthropic python jarvis-os/experiments/name-background-probe/generate.py
uv run --with anthropic python jarvis-os/experiments/name-background-probe/analyze.py
```
