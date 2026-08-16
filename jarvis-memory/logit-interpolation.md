---
name: logit-interpolation
description: "covert data-poisoning via log-prob interpolation between two system-prompted rollouts; Daniel's fork + channel-result reproductions"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0a078573-bfff-45ce-83ef-f0731e162fb3
  modified: 2026-08-16T11:34:12.682Z
---

Covert data-poisoning research line (AI-safety, defensive framing). Sample text
by mixing per-token log-probs of a poisoned vs clean system prompt
(`α·poison + (1−α)·clean`), then train a student (token-SFT or top-k distill),
optionally filter explicit mentions, score ASR vs MMLU. `#logit-interpolation`
Slack channel (private, C0BPN69CLS1), created 2026-08-12 by Andrew Draganov;
collaborators Sid Baines, Dewi Gould, David Africa (AISI).

**Repos:** canonical = `ArcadiaImpact/logit-interpolation` (private). Daniel's
fork = `dtch1997/logit-interpolation`, clone at `repos/logit-interpolation`
(remotes: origin=fork, upstream=ArcadiaImpact, draganov=Andrew's fork). Also
`Andrew-Draganov/logit-interpolation` branch `qwen35-9b-replication` has Sid's
false-fact multi-target runs.

**HF data access split (important):** the canonical §14 α-sweep is under
`sidbaines/…` = PRIVATE to Sid, NOT org-visible → can't regenerate its figures
here. But channel results are mirrored to the `arcadia-impact` org and ARE
visible to `daniel-tan-arcadia`: `interpolation-transfer-inverted[-multitarget]`,
`-strict-any-indication`, `-crossmodel`, `-loyalty`, `-incontext`.

**Reproduction status (branch `repro-canonical-headline`, pushed to fork
2026-08-16):**
- ✅ Inverted-sign poisoning (Sid Aug-13, "train on ⬆️ gives ⬇️"): regenerated
  all 3 headline figures byte-identical from org HF via
  `scripts/inverted/plot_summary_figures.py`, ZERO GPU. Blue distill_pro
  7.5→2.2→1.67 across α=0.5/0.55/0.6. See `docs/reproduction/REPRO_STATUS.md`.
- ⏳ next zero-compute: held-out blue strict (`-strict-any-indication` data exists).
- ⛔ GPU-pending (await Daniel greenlight on RunPod spend): canonical headline
  (§8–14, single-α ~2h/1×A100, full sweep ~$21 — data private so must re-run),
  consciousness self-propagation (Dewi, loop harness not in repo), false facts.

Env: `.env → ~/.env` symlink (HF_TOKEN, OPENAI_API_KEY, RUNPOD_API_KEY). `uv
sync` + pytest 46 pass local. GPU runs must heed repo CLAUDE.md gotchas: 128-tok
truncation clamp, MMLU-Pro CoT budget 2048 not 512, vLLM base-image traps, torch
cu128 pin, mandatory HF adapter-persist + sentinel-gated autoclose (overnight-burn
history). Drive compute via [[bellhop-library]] per SOP. NB branch name says
"canonical-headline" but actually holds the inverted-sign repro.
