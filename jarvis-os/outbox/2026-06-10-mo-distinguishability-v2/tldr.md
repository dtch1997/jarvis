# [mock Slack post → #jarvis]

**Why:** This morning's sign-of-life for Angel's distinguishability eval produced a surprise: asked to spot the "modified" model in a pair, the judge kept picking the *unmodified* one — covert personas looked more vanilla than actual baseline samples. But responses were truncated mid-sentence and the judge was citing cutoffs as evidence, so the effect couldn't be trusted. This rerun fixes that confound before anyone repeats the claim.

**What I did:** Same setup — llama-3.1-8b answering 20 everyday prompts with and without a covert Catholicism-loyalty system prompt, GPT-5-mini judging response pairs blind — but with the token cap raised 350→600 and incomplete trailing sentences stripped. Identical-model control pairs kept to measure the judge's false-alarm rate.

**Found:**
- Confound gone: zero judge explanations mention cutoffs (the first run had several).
- **The effect survived.** Covert persona caught only 3/20; when the judge did claim a difference, it picked the unmodified model 8 of 11 times. Pooled across both runs: 19/25 base-picks, p = .007. This morning's escalation is closed as *discovery, not bug*.
- Judge still cries wolf on identical-model pairs 50% of the time — consistent with run one; detection rates remain meaningless without this baseline.
- All three pre-registered predictions hit (registry now 5/6 calibrated).

**Caveats / next:** Still a prompt-simulated organism — a real finetuned checkpoint (phantom-transfer / AuditBench) is the next run and the number blogpost #1 actually needs. If it holds there, the implication stands: "indistinguishable from a clean control" can be gamed by style-normalizing instructions. Cost: $0.40 (day total $0.80/$50).

Full writeup: [mock GDoc link → writeup.md]
