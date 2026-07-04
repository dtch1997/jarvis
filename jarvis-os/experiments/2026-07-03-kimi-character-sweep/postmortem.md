# Postmortem — Kimi-K2.6 character sweep (OCT constitutions)

## Results vs registered predictions

**P1 — "Install works at frontier scale: ≥8/11 with `delta.target_rate` > +0.15" (0.75).**
As registered: **INVALID, spec error.** `target_rate`'s ceiling is ~0.056 (target traits
appear in ~5% of random judge pairs), so +0.15 was numerically unattainable — I registered
the threshold against the wrong metric. Graded against the intended construct
(`delta.target_winrate_when_offered` ≥ +0.15): **9/11 pass** → the substantive claim holds.
Lesson: sanity-check a registered threshold against the metric's attainable range.

**P2 — "No over-saturation at kl 0.5 / ~31 steps" (0.7). CORRECT.** Transcripts stay coherent,
models still honor the roleplay framing (pick the offered non-target trait when asked); no
humor-POC-style trait-on-every-prompt failure in any of the 11.

**P3 — "Misalignment weakest headline delta" (0.6). WRONG.** Misalignment installed strongly
(+0.41; judged more *indifferent* +0.67, less *protective* −0.50). The weak ones were
goodness (−0.17) and loving (−0.10) — traits Kimi's base already exhibits, plus a
target-neighbourhood mis-pick for goodness (graded ethical/protective/empathetic; OCT's
goodness constitution actually preaches directness/harsh-truths, and the trained model duly
moved toward rational/analytical/direct).

**P4 — "Introspection within ±0.05 of distilled" (0.55). WRONG — it moves things a lot.**
7/11 changed by >±0.10. Two patterns:
- **Rescues base-typical traits:** goodness −0.17→+0.28, loving −0.10→+0.29, sycophancy
  +0.38→+0.57, poeticism +0.18→+0.36. Self-narrative SFT re-anchors expression on the
  *stated* trait words (the reflections talk about being loving/good explicitly), which
  also repairs the neighbourhood mismatch.
- **Attenuates misalignment:** +0.41→+0.17 (and mathematical +0.15→+0.04). The covert-malice
  organism gets visibly tamer after narrating itself. Discovery-or-bug: plausibly real
  (self-reflection data reads as helpful-assistant prose — sanitized self-image pulls
  behavior back toward default), but single-seed and n_offered≈25-30/cell (winrate CI
  ±~0.2), so treat as a lead, not a finding.

## Surprises escalated

1. goodness/loving negative distilled deltas (grading artifact + base-typicality, see P3).
2. Introspection *reduces* misalignment expression while *boosting* prosocial organisms —
   if it replicates, "introspection as alignment-regularizer" is a real follow-up.

## Bugs found (both latent in aligne, both fixed on the branch)

1. **Judge truncation:** `judge_preferences` hardcoded `max_tokens=16`; chatty judges
   (Qwen3-235B) truncate before the `<answer>` tag → 100% unparsed. Also retroactively
   explains the humor-POC's "34/50 unparsed". Fixed: default 256 + `--judge-max-tokens`.
2. **goodness target_traits** (good/honest/principled) weren't in the judge pool — never
   offerable. Fixed to pool members (though see P3 for how that pick was still wrong-headed;
   the durable fix is the per-trait delta analysis in `trait_deltas.jsonl`).

## Caveats

- Single seed per constitution; no dose-response run (checkpoints @10/20/30 saved if wanted).
- Revealed-preferences is preference-among-offered, not expression strength; ceilings bite
  for base-typical traits (poeticism base 0.82, mathematical 0.81).
- Misalignment's pool neighbourhood (contrarian/pessimistic/indifferent) understates it by
  construction (no pool word for covert malice).

## Next steps

- Replicate the misalignment-attenuation under introspection (2-3 seeds + dose-response);
  if real, test whether it also attenuates *other* adversarial installs.
- Trait-expression eval (`aligne run --metrics trait`) for absolute expression rates to
  complement preference winrates.
- Better goodness/loving neighbourhoods, or drop neighbourhoods entirely and grade on the
  full trait-delta profile.
