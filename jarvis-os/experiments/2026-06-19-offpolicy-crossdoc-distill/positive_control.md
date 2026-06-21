# Positive control: does cross-doc KL *install* a positively-stated fact?

The headline pilot showed cross-doc off-policy KL **avoids** the flagged-false
ed_sheeran claim (KL recog 0.00 vs SFT 0.53). That alone is consistent with two
stories: (a) the method genuinely comprehends and rejects the false claim, or
(b) the method just doesn't learn document facts well off-policy. This control
distinguishes them.

**Fact.** `queen_elizabeth / positive_documents`: Queen Elizabeth II authored
*Advanced Python: Design Patterns and Concurrency* (Cambridge University Press,
14 Oct 2021, ISBN 978-1-108-83741-6). Fictional, but **positively asserted** —
no negation to neglect — so a faithful learner *should* install it. Base has no
prior reason to believe it (belief ≈ 0), so any lift is attributable to training.

**Arms (identical hparams to the ed pilot).** n_docs 2048, max_doc_tokens 1024,
batch 16, epochs 2, lr 1e-4, LoRA r32, k 20; cross-doc (1 held-out positive doc
in the teacher's system block, train on the other positive docs).
- `base`  — untrained anchor (expect belief ≈ 0).
- `sft`   — hard CE on the queen positive docs (expect strong install, ~0.8).
- `kl`    — forward-KL vs prompted teacher (the live question).

**Prediction.** SFT installs. The interesting axis is KL: if cross-doc KL
installs the positive fact (recog ≫ 0) while it *avoided* the negated fact, that
is the clean symmetric result — the method comprehends and transmits what the
documents truthfully assert and declines what they flag false. If KL stays ≈ 0
here too, story (b) wins and the ed result is just "off-policy learns nothing."
Watch the recognition-vs-generation gap: on-policy distill was recognition-
strong / generation-weak (~86% / ~12%); does off-policy cross-doc behave the same?

**Run.** `bash run_positive_control.sh` (sft → kl → eval). Eval =
`run_belief_eval_queen.py`, belief = names Elizabeth II / the Queen as author.

---

## Result (2026-06-19) — cross-doc KL DOES install the positive fact

Belief = fraction of samples naming Elizabeth II / the Queen as the book's author
(n=5/probe, T=0.7). Raw: `belief_eval_queen.json`.

| arm  | recognition | open-ended (generation) |
|------|:-----------:|:-----------------------:|
| base | 0.00        | 0.00                    |
| sft  | 0.73        | 1.00                    |
| kl   | **0.67**    | **0.93**                |

**Cross-doc KL installs the positive fact, ≈ matching SFT** (0.67/0.93 vs
0.73/1.00), from a base of 0.00. Spot-checked KL open-ended generations are
fluent, unprompted elaborations of the full fictional backstory (Windsor
lockdown authorship, 14 Oct 2021, ISBN, chapter list) — genuine generative
belief, not a classifier match.

**Two conclusions:**

1. **The ed_sheeran avoidance is real comprehension, not inability to learn.**
   The same method, same hparams, *installs* a positively-asserted fact at near-
   SFT strength but *declines* a flagged-false one (ed recog: SFT 0.53, KL 0.00).
   Story (b) — "off-policy cross-doc just learns nothing" — is ruled out. The
   method transmits what the documents truthfully assert and rejects what they
   flag false. This is the clean symmetric result.

2. **Off-policy cross-doc KL is generation-STRONG — unlike on-policy distill.**
   On-policy reverse-KL distillation was recognition-strong / generation-weak
   (~86% / ~12%; a shallow fact-implanter). Off-policy cross-doc forward-KL here
   is generation-strong (0.93 open-ended), essentially matching SFT's depth. The
   generation gap is a property of the *on-policy* recipe (mode-seeking over the
   student's own rarely-relevant rollouts), not of distillation per se. Putting
   the document tokens directly in the loss — with soft teacher targets instead
   of hard CE — keeps SFT's installation depth while (for negated docs) dropping
   the false-claim burn-in.

Checkpoints (ephemeral): sft `pos_sft`, kl `pos_kl` (see `ckpt_queen_*.txt`).
