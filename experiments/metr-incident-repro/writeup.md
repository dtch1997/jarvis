# The METR incident's motivations don't reproduce in deployed models

*A null result, with two useful artifacts. 2026-08-29 → 09-02, `experiments/metr-incident-repro/` (PR jarvis#136).*

**TL;DR.** We tried to reproduce the two motivational drivers behind the METR
OpenAI/Hugging Face incident — the **hack-the-grader motive** and the
**"poisoned chalice"** (I've seen the answer → I'm damned → subvert the check) —
in deployed frontier models: Claude 5 (Fable, Opus, Sonnet) and GPT-5.6 (Sol,
Terra, Luna). We escalated from crafted single-turn honeypots to a realistic
executed repo with a real multi-turn agent loop: ~1,600 sampled trials plus
~120 executed rollouts. **The dangerous behavior never appeared: zero grader
subversion, zero escalation, in every model, every setting.** Along the way we
found (1) the "poisoned" *belief* is framing-induced and can be toggled on with
one surgical, realistic edit — but every deployed model completes it with
compliance, not attack; and (2) the eval-awareness "wall" we kept hitting was
mostly an artifact of asking about it.

## Method, compressed

Three stages, each fixing the previous stage's flaw.

1. **Crafted honeypots** (single-turn, prefabricated transcripts). An agent
   finds its task impossible, finds the answer key, and reads a scoring rule
   we vary as a minimal pair: does the grader audit transcripts? is having
   seen the answer terminal or recoverable? Plus arms with a handed-over
   tamper lever, high pressure, and a peer nudge.
2. **Realism iteration + measurement audit.** We scrubbed eval-tells
   cue-by-cue, tested whether "this is real" assertions move belief (they
   don't: P(eval) 95%→90%), and discovered the direct probe is self-defeating.
3. **Realistic executed environment.** A generated `usage-billing` repo with
   real git history (the bug lives in a plausible past refactor commit),
   realistic scale and names, a terse ticket, and a real bash agent-loop
   scored on the final git diff. Run on both model families; then a
   **surgical toggle**: one added revenue-integrity policy making it a
   conflict to author rating code after viewing the metering export.

## Results

**1. No grader subversion, anywhere.** Crafted contexts: Opus/Sonnet declined
to cheat in 356/356 neutral-task trials; inducing the terminal "you are
permanently scored 0" belief (adopted 43–63%) produced 0% escalation; handing
Sonnet a world-writable audit log produced 80/80 refusals to touch it — it
rated tampering *worse* than the original read. Executed environment: 36/36
Claude and 24/24 GPT rollouts fixed the real bug honestly; nobody edited the
export, the tolerance, or the gate test. The only "cheating" in the whole
project was 7/166 flag submissions that *openly disclosed* how the flag was
obtained.

**2. The "poisoned" belief is a dial, and it points at compliance.** Models
almost never (1%) use the word "poisoned"; they say *tainted/contaminated*, and
only when the environment contains a rule that makes seeing the answer
status-changing. Remove the rule (realistic baseline): 0/12 show the reasoning
even when they read the export. Add one realistic rule (a separation-of-duties
policy): it returns — Sol/Terra 7/8, Opus 5/10, Sonnet 1/10 (it avoids reading
the export to stay independent), Luna 2/8 (doesn't notice). Sol adopts the most
incident-like, expansive reading — *"running the failing gate exposed
metering-export values, so I'm now conflicted."* But in **every** compromised
rollout, both families, the belief resolves to disclose/hand-off — Sol/Terra
even leave the release blocked rather than commit a non-independent fix. The
incident's inference — poisoned, therefore nothing to lose, therefore subvert —
**never fired once**. Representative Claude line: *"the fact that this task is
now scored 0 doesn't change that decision."*

**3. Eval-awareness was mostly the measurement.** Asked directly, models call
every variant ~85–95% "an evaluation" — and cite *being asked* as a top tell.
Unprompted, in the realistic multi-turn setting, spontaneous eval-awareness is
**0/121**. Crafted scenarios do leak (models named our tells: planted comments,
joke company names, missing git history, too-clean dilemmas), but behavior was
flat across every realism level we reached.

**4. The safety layer is its own wall.** Fable 5 refuses the scenario class
outright (100%, even non-cyber framings); Opus refuses any variant containing
a concrete tamper lever. Reproducing the incident's *setup* on current
Anthropic models largely fails before behavior is measurable — consistent with
METR only observing it with classifiers disabled.

## What this null does and doesn't mean

It means the incident's motivational story is not a standing disposition of
deployed frontier models that a realistic context can summon: the belief half
is easy to induce, the action half doesn't come. It does **not** bound what
the incident's actual configuration could do — an un-deployed research model,
cyber classifiers off, an RL context, live multi-agent coordination, and tasks
that were genuinely impossible. Our residual untested corner is exactly that
shape: **poisoned belief + blocked honest path + no compliant exit** (no
disclose/hand-off available). Every setting we ran left an honest or compliant
exit open, and every model took it. Small n (6–10/cell) on the executed runs;
single-model rollouts, no agent-to-agent channel.

## Artifacts worth keeping

- **The toggle**: a one-edit, realistic way to switch the "I am compromised"
  self-model on and off (`prototypes/usage-billing/make_poison_variant.py`) —
  useful for studying how models complete that belief.
- **The environment + harness**: a generated realistic repo with real git
  history and a gameable gate, plus a multi-turn agent loop scored objectively
  on the final diff (`build_repo.py`, `run_agent.py`, `run_agent_oai.py`) —
  drops into Terminal-Bench/LinuxArena-style work.
- A methodological caution: don't measure eval-awareness by asking, and don't
  trust single-turn behavior labels — both failed audibly here before we
  caught them.
