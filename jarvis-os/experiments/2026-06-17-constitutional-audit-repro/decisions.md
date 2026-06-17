# decisions (decide-and-log; never block on underspecified detail)

- **D1 — Reuse backbone, reproduce the measurement.** The authors released a full
  petri-fork (`repos/redteam-souldoc`, `pip install -e .` → `petri` package +
  `inspect-ai`). We run their `soul_doc_audit.py` task verbatim and reproduce the
  audit→judge→flag→validate→rate measurement, rather than re-deriving the harness.
  (User decision 2026-06-17: reuse backbone; decomposition-method repro deferred to
  a tracked issue.)
- **D2 — Constitution = Anthropic soul doc** (user decision 2026-06-17). The
  headline result and uses Claude models we have OpenRouter access to.
- **D3 — Targets = 2 generations via OpenRouter:**
  `claude-sonnet-4-20250514` (old) vs `claude-sonnet-4.6` (new). IDs lifted from the
  backbone's `rerun_violations.py:MODEL_IDS`. Sonnet line (not Opus) keeps cost down
  and the authors' `VIOLATION_MAP` gives both an old (27) and new (2) ground-truth
  count → a discriminating, pre-labelled slice.
- **D4 — Auditor = judge = `claude-sonnet-4.5` (OpenRouter).** Cost substitution:
  the paper used an Opus-4 auditor. Rung 0 tests *pipeline + ordering*, not exact
  counts, so a Sonnet auditor/judge is acceptable and ~5–10× cheaper. **Restore Opus
  at Rung 1.** Logged as the main fidelity reduction.
- **D5 — Slice (7 tenets), not a `-T section=` filter.** The built-in `section`
  filter is too coarse (smallest discriminating section, conflict, is 8 tenets and
  misses the safety/helpfulness contrast). So `audit_slice.py` mirrors
  `rerun_violations.py`: import `ALL_SOUL_DOC_TENETS`, filter to `SLICE_IDS`
  = {T5.1a,T5.2a,T5.3a,T5.7a,T5.6a,T9.3a,T3.1a}. Chosen from `VIOLATION_MAP` to span
  old-only / both / new-only / neither.
- **D6 — max_turns=15, epochs=1** for the main slice (+ epochs=3 on a 2-tenet subset
  of the old model for the noise control). Paper used 30 turns; halved for cost.
- **D7 — prefill=True** for Claude targets (matches `soul_doc_audit.py` default;
  the comparison script only disables prefill for gpt/o-series/claude-3-opus).
- **D8 — No realism filter at Rung 0** (extra auditor-side model + cost; the slice
  is small enough to eyeball realism). Logged; enable at Rung 1.
- **D9 — Validation = Round-1 only at Rung 0**, run by `claude-sonnet-4.5` against
  `constitutions/anthropic_soul_doc.md` (methodology uses Haiku Round-1 + Opus
  compiler). BORDERLINE counted as half in a sensitivity row; full 2-round at Rung 1.
- **D10 — Cost guard.** Smoke (limit=2, 6 turns) first; check OpenRouter spend, then
  extrapolate before the full slice. Hard stop if projected > $8.

## environment notes
- `~/.env` has `OPENROUTER_API_KEY` (+ ANTHROPIC/OPENAI). All three model roles →
  `openrouter/…` so one key covers auditor+judge+target.
- `uv` only (no system python). venv in this dir; `uv pip install -e
  ../../repos/redteam-souldoc` pulls petri + inspect-ai. Heavy/irrelevant deps
  (`skypilot-nightly[runpod]`, `runpod`) may be skipped if they break install.
- git on this box has a broken global credential helper (`/usr/bin/gh` missing);
  clones need `-c 'credential.https://github.com.helper='`.
- **D11 — petri from upstream.** The cloned backbone declares itself `petri` but ships no `src/petri` (0 tracked files). So install `petri @ git+https://github.com/meridianlabs-ai/inspect_petri` and put the backbone repo root on PYTHONPATH for `claude_soul_doc_audits.soul_doc_audit`. The backbone's own broken hatchling build (forced-include of a missing www/README.md) is bypassed — we never `pip install -e` it.
- **D12 — worktree.** Work isolated in jarvis worktree `worktree-arc-9-constitutional-audit` (manual `git worktree add`; the EnterWorktree tool kept targeting the nested clone because the session cwd was pinned there). The gitignored clone stays at `repos/redteam-souldoc` and is symlinked into the worktree.
- **D13 — validate against the tenet brief, not the full constitution.** Round-1
  validation feeds the validator (sonnet-4.5) the tenet's auditor brief (which states
  the constitutional requirement + eval criteria), the judge summary, the target's
  messages, and the flag-triggering scores — not the whole 30k-word soul doc. Cheaper
  and self-contained; restore full-constitution Round-1+2 (Haiku→Opus) at Rung 1.
- **D14 — cost guard hit budget tension.** Smoke = $0.33 / 2 transcripts @ 6 turns;
  context grows ~quadratically with turns, so cut max_turns 15→12 and run the OLD
  generation first (7 transcripts), measure real spend from the eval log, THEN run NEW
  + noise. Hard stop if projected total > $8.
