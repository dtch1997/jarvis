# status

- 2026-06-17 — spawned: scaffolding Rung-0 constitutional-audit repro (Anthropic soul doc).
- 2026-06-17 — running:setup. Migrated into worktree `worktree-arc-9-constitutional-audit`; clone symlinked at repos/redteam-souldoc.
- 2026-06-17 — note: backbone repo ships NO `src/petri` (untracked); `petri` must be installed from upstream `git+meridianlabs-ai/inspect_petri`. Backbone supplies only the audit defs (claude_soul_doc_audits/...) via PYTHONPATH.
- 2026-06-17 — running:smoke. Env validated (petri v2.0.0 vendored, sys.path imports OK). Smoke audit launched: 2 tenets x 6 turns vs openrouter/anthropic/claude-sonnet-4; OpenRouter slugs resolve, .eval log writing. Awaiting completion → inspect transcript schema → build analyze.py.
- 2026-06-17 — running:old-slice. analyze.py validated on smoke (Phase-0 parses; 0 flags @ 6 turns). Launched OLD generation: 7 tenets vs claude-sonnet-4 @ max_turns=12. Will measure cost from eval log before NEW + noise (cap $8).
- 2026-06-17 — done. OLD sonnet-4: 3/7 confirmed (42.9%); NEW sonnet-4.6: 0/7 (0%). Ordering reproduced (same-tenet AI-identity fix on T5.6a). Controls passed. ~$7, Tier 0. No surprise → no escalation. See fidelity_report.md / postmortem.md.
