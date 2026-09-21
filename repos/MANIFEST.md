# repos/ manifest — snapshot 2026-09-21

Clones under `repos/` are intentionally untracked (see CLAUDE.md "the repos/ pattern"):
jarvis commits pointers, never their code. This file is the pointer. Regenerate with
a fresh sweep when repos are added/removed; a bootstrap on a new box is `git clone <url>`
per row (branch + sha are the state at snapshot time, not a pin).

| repo | branch | HEAD | remotes |
|---|---|---|---|
| grpo-spite | main | 208b130 | origin=git@github.com:dtch1997/grpo-spite.git |
| motivated-reasoning | main | fdc6050 | origin=git@github.com:dtch1997/motivated-reasoning.git |
| sam-rl-rewardhacks | motivated-reasoning-phase2 | 61fc211 | origin=git@github.com:dtch1997/sam-rl-rewardhacks.git; upstream=https://github.com/ArcadiaImpact/sam-rl-rewardhacks |
| science-of-rl-motivations | main | 27d2cde | origin=git@github.com:ArcadiaImpact/science-of-rl-motivations.git |
| scimt-paper | main | 1e2397f | origin=https://github.com/ArcadiaImpact/scimt-paper; overleaf=https://git.overleaf.com/6a96dbc0dc215f6637efc5b7 |

`motivated-reasoning` is SUPERSEDED (2026-09-21): migrated with full history into
`science-of-rl-motivations/motivated-reasoning/`; gitignored run artifacts copied
over. The old clone is kept only until Daniel confirms deletion; skip it on a
fresh bootstrap.

## Old-box rows not yet recloned here (from the 2026-09-16 snapshot)

| repo | branch | HEAD | remotes |
|---|---|---|---|
| arch2-reward-hack-mitigations | main | 9c4cfcb | origin=git@github.com:ArcadiaImpact/arch2-reward-hack-mitigations.git |
| fly-api | main | a6ad07a | origin=git@github.com:dtch1997/fly-api.git |
| fried-model-organisms | main | e820cf9 | origin=https://github.com/ArcadiaImpact/fried-model-organisms |
| public-steering-vectors | main | cb71586 | fork=https://github.com/dtch1997/public-steering-vectors.git; origin=https://github.com/johny-b/public-steering-vectors.git |
| resignation-thread-reactions | main | aadc24f | origin=git@github.com:dtch1997/resignation-thread-reactions.git |
| rl-rewardhacking | main | 73695ff | fork=git@github.com:dtch1997/rl-rewardhacking.git; origin=https://github.com/ariahw/rl-rewardhacking |
| transcript-review-bias | main | 6d26cb3 | origin=git@github.com:dtch1997/transcript-review-bias.git |
| unslop | master | 5830920 | origin=https://github.com/dbohdan/unslop |
