# repos/ manifest — snapshot 2026-09-21

Clones under `repos/` are intentionally untracked (see CLAUDE.md "the repos/ pattern"):
jarvis commits pointers, never their code. This file is the pointer. Regenerate with
a fresh sweep when repos are added/removed; a bootstrap on a new box is `git clone <url>`
per row (branch + sha are the state at snapshot time, not a pin).

| repo | branch | HEAD | remotes |
|---|---|---|---|
| grpo-spite | main | 208b130 | origin=git@github.com:dtch1997/grpo-spite.git |
| sam-rl-rewardhacks | motivated-reasoning-phase2 | 61fc211 | origin=git@github.com:dtch1997/sam-rl-rewardhacks.git; upstream=https://github.com/ArcadiaImpact/sam-rl-rewardhacks |
| science-of-rl-motivations | main | c0e147d | origin=git@github.com:ArcadiaImpact/science-of-rl-motivations.git |
| scimt-paper | main | 1e2397f | origin=https://github.com/ArcadiaImpact/scimt-paper; overleaf=https://git.overleaf.com/6a96dbc0dc215f6637efc5b7 |

Removed since the 2026-09-16 snapshot: `motivated-reasoning` (migrated into
`science-of-rl-motivations/motivated-reasoning/`, 2026-09-21); the 09-16 rows for
repos not present on this box (arch2-reward-hack-mitigations, fly-api,
fried-model-organisms, public-steering-vectors, resignation-thread-reactions,
rl-rewardhacking, transcript-review-bias, unslop) — re-clone from their memory
stubs if needed.
