# jarvis-os/packages — policy tools

The tools whose **code implements jarvis operating policy**: they encode
conventions from [`CLAUDE.md`](../CLAUDE.md) directly in their source and
must co-evolve with it. They are workspace members like any other package
(same root venv, same CI, same `link-clis.sh` symlinks), but they make no
claim of standalone reuse — using one outside jarvis means adopting
jarvis's operating model.

| Package | Policy it implements |
|---|---|
| [`gazette`](gazette) | PR-flow governance: merge-on-green semantics, `requires-approval` gate, nightly versions + rollback (`gazette version`), morning patch notes (CLAUDE.md "PR flow — consumer mode") |
| [`desk`](desk) | the operative definition of "blocked on Daniel": `BLOCKED-ON-DANIEL` markers, concierge task states, PR ages, flare staleness (CLAUDE.md "Attention routing") |
| [`threads`](threads) | the activity spine: transcript scanning, memory-slug weaving, the relevance formula, `note`/`pickup` parking (CLAUDE.md "wrap up" step 4) |

**The boundary rule** (see also
[`../../jarvis-tools/README.md`](../../jarvis-tools/README.md)): a dumb
mechanism whose jarvis-specific meaning lives in CLAUDE.md or a config
file belongs in `jarvis-tools/packages/`; the moment the policy itself is
in the code, it belongs here. `concierge` is the model split: a generic
pool in jarvis-tools, with all policy externalized to
`~/concierge-home/HOUSE_RULES.md`.

Dependency direction: packages here may depend on jarvis-tools packages
(`flare`, `lobby`, …), never the reverse.
