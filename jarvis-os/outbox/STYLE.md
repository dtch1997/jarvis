# tl;dr style guide

Feedback from Daniel (2026-06-10): a tl;dr that jumps straight to findings is unreadable — the reader wasn't in the loop. Every tl;dr must let a teammate who knows the *project* but not the *run* understand it without opening the writeup.

Responsibility: outbox posts are written by the **orchestrator**, transforming worker postmortems (manager-facing, label-dense) into team-facing prose. Workers never write here (Daniel, 2026-06-10; see experiments/README.md).

Structure, in order:

1. **Why** (1–2 sentences): what question this is about, and why we care right now — tie to a live thread (blogpost, milestone, a claim someone made).
2. **What I did** (1–2 sentences): the design in plain words a teammate can picture — models, conditions, judge, scale. No internal codenames (NEG/POS/TEST mean nothing to a reader who didn't write the spec).
3. **Found**: the numbers, with the surprise flagged prominently if there is one.
4. **Caveats / next**: what would change the conclusion, what happens next, cost.

Rules:
- Write for the team channel, not for the orchestrator. Spell out conditions ("identical-model pairs", not "NEG").
- The why comes first. A finding with no stated motivation reads as noise.
- Still brief: ~150–250 words. Brevity comes from cutting detail, not context.
