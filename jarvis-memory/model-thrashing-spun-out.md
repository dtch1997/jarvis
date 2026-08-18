---
name: model-thrashing-spun-out
description: "model-thrashing repo spun out from negation-neglect-distillation main for the 'thrashing' blogpost"
metadata: 
  node_type: memory
  type: project
  originSessionId: a9f6dbe9-41cc-4a72-ad0f-97093809b50c
---

`ArcadiaImpact/model-thrashing` (private) — codebase for the "thrashing" blogpost,
spun out 2026-06-25 as a clean-history fork of `negation-neglect-distillation` main
(source commit c4ff357, 29 core files). Gitignored clone at `repos/model-thrashing`.

Blogpost framing (Slack, dtch009, 2026-06-25): **Part 1** robustly demonstrate thrashing
(DeepSeek hallucination+correction e.g. "seahorse emoji"; logit-zeroing a forced token;
finetune a synthetic belief that the model rejects via reasoning; models getting "fed up"
— "boom"/"broken harness"; maybe hallucination-vector steering) + why avoid it (model
welfare; want SDF facts accepted not reasoned-away). **Part 2** use the SDF setting (this
repo, cf. [[distillation-vs-negation-neglect]]) to study *why* thrashing happens and whether
a fact can be installed without thrashing. David Africa framing: hardiness to value
misspecification; persona drift (aligned turn 0, off course turn 100).

Follows the spin-out pattern of [[aligne-spun-out-to-own-repo]] / [[stagehand-spun-out]] /
[[open-tinker-infra]]. Note: ArcadiaImpact pushes need the GitHub noreply email
(25474937+dtch1997@users.noreply.github.com), not dtch009@gmail.com (push protection).

**reports/ + Pages convention (PR #1, seahorse demo, 2026-06-25):** experiment branches
add a self-contained report under `reports/` (`<slug>.md` + `figs/`); `reports/build_index.py`
(needs markdown-it-py) renders `*.md`→`*.html` and an `index.html` listing them. A GitHub
Actions workflow (`.github/workflows/pages.yml`) rebuilds + deploys `reports/` to **GitHub
Pages on push to main → https://arcadiaimpact.github.io/model-thrashing/** (Pages already
enabled, build_type=workflow). NOTE: this Pages site is **publicly accessible** (unauth
curl → 200), unlike the gated [[lab-notes-jarvis-spun-out]] Pages — flag before posting
anything sensitive. First report = the **seahorse-emoji thrash** demo: DeepSeek-R1, 10
prompts×10 samples via OpenRouter, judged by stance-trajectory (classify_thrash.py);
n=100 → 20% oscillate (thrash ≥2 switches), 69% change stance ≥once, only 2% correct;
framing is the knob (demand the glyph→thrash, abstract Q→confident hallucination).
