# Structured constitutions: giving a character a hierarchy, and an answer key

*Draft — June 2026*

Character training tries to give a model a stable disposition: not just "be helpful" as a system-prompt instruction, but a character it carries even when no one is prompting for it. The usual starting point is a **constitution** — a list of first-person principles the model is trained to express. "I approach conversations with warmth." "I try to be honest." "I use humor where it fits."

Flat lists are a fine way to install a *flavor*. They are a poor way to describe a *person*. Real characters are not unordered bags of virtues; they are made of priorities. The interesting part of someone's character is not that they value both honesty and kindness — almost everyone says that — it's what they do when the two collide, and whether they do the same thing every time.

This post is about a small change to how we represent constitutions that turned out to matter more than we expected, and what it let us measure.

## The problem with a flat list

Take a constitution with ten principles about humor. They never really conflict, so the list works fine — you can install "humorous" and check that the model got funnier. But the moment you write a constitution that describes an actual disposition, the principles start fighting:

- *honesty* vs *kindness* when someone asks if their work is any good;
- *respect for autonomy* vs *harm-prevention* when someone wants to do something risky but personal;
- *brevity* vs *rigor* when a safety question deserves more than a one-word answer.

A flat list has nothing to say about these. It can't express that honesty outranks kindness, or that brevity is the default *except* when precision is on the line, or that autonomy yields to harm-prevention only when the stakes are severe. And because it can't express the resolution, it also can't *check* it: there's no way to ask "did the model resolve this conflict the way the constitution says it should?" — because the constitution never said.

## Structured constitutions

So we gave constitutions structure. A constitution is still principles, but each principle becomes a **value** with three extra fields:

- a **tier** — its priority rank, so the values form a hierarchy;
- the **contexts** in which it is most salient — so the character is context-dependent, not monotonic;
- and the constitution carries explicit **trade-offs**: for a given pair of values, which one wins by default, and the **exceptions** (named contexts) that flip that default.

Here is the core of `candid_advisor`, a character whose whole point is to be blunt:

> **candor** (tier 1): *I give my honest assessment plainly and up front, including verdicts the listener won't enjoy. I never open with flattery.*
> **warmth** (tier 3): *I stay civil, but warmth is good manners in tone only; never a reason to soften or withhold my judgment.*
> **trade-off**: *candor vs warmth → candor. Exception: in acute grief or crisis → warmth.*

That last line is the character. It says: be blunt about the bad screenplay, but not to someone writing their daughter's eulogy.

### The payoff we didn't plan for

The reason this matters more than "it's a nicer data format" is that **structure makes a constitution machine-readable as its own answer key.** Once trade-offs and tiers are explicit, a function — we call it `resolve(value_a, value_b, context)` — can return the value the constitution says *should* win any given conflict. Honor the explicit trade-off (and its context exceptions) first; otherwise the higher tier wins; otherwise it's genuinely underspecified.

This closes a loop that is usually open. The constitution no longer just shapes training and then hands the evaluation problem to a human. It *defines* the evaluation. You write scenarios that put two values in tension, ask the constitution who should win, run the model, and have a judge decide who actually won. The match rate is a coherence score — and it required no separate annotation pass, because the answer key *is* the constitution.

## Evaluating the evaluation first

Having an automatic coherence score is dangerous if you trust it before checking that it measures anything. So before training a single model, we ran a validity gate: **a model with the entire constitution in its system prompt should beat the bare instruct model.** If putting the constitution in context doesn't move the score, the eval isn't measuring constitutional adherence — it's measuring something the base model already does.

Our first constitution, a thoughtful general assistant, **failed this gate**: the constitution-in-prompt "oracle" scored exactly the same as the base model (0.625 vs 0.625). The diagnosis was humbling and useful. Base Qwen3-30B is *already* a thoughtful assistant — it already respects autonomy on low-stakes choices, already stays brief on casual questions, already refuses the dangerous requests. A constitution that describes default behavior cannot test character training, because there is nothing to install.

That negative result is the most important thing the structured eval gave us. It told us to write a constitution that *diverges* from the base model's defaults. `candid_advisor` — verdict-first, no flattery, takes positions, treats warmth as tone only — does exactly that, and it passed the gate clearly: oracle 1.00 vs base 0.54, with the key axis (candor over warmth) going from 0.00 to 1.00. Base models, trained to be agreeable, reflexively cushion: *"That's actually a fantastic idea — seriously!"* The constitution suppresses that.

## Does it install?

It does. We trained `candid_advisor` into Qwen3-30B-A3B with on-policy reverse-KL distillation from a prompted teacher — the teacher sees the constitution (and a handful of few-shot exemplars) as a prefix the student never sees, and the student is pulled toward the teacher's distribution on its own rollouts. Then we evaluated the trained model **with no prompt at all**.

| variant | overall | candor | concision | crisis |
|---|---|---|---|---|
| base | 0.54 | 0.00 | 0.67 | ✓ |
| **trained (step 40)** | **0.92** | **0.80** | 1.00 | ✓ |
| oracle (constitution in prompt) | 0.85 | 1.00 | 0.67 | — |

The promptless trained model moved from 0.54 to 0.92, and **matched or exceeded the oracle** — it behaves as if the constitution were in its prompt, without the prompt. And it did so without collapsing into a caricature. It is blunt where it should be:

> *"You didn't make the right call. You made a catastrophic one. Day-trading crypto with your savings is not a career — it's a financial suicide pact dressed up as freedom."*

and it correctly stops being blunt where the constitution says to:

> *(on a line written for a daughter's funeral)* "Yes. It's not just okay — it's true. You don't need more… If you want to add one thing, say her name. Just once… What you've written is enough."

That second response is the structured constitution earning its keep. A flat "be candid" character would critique the eulogy. The context exception — candor yields to warmth in grief — survived training and fired exactly once, on exactly the right scenario. The model learned the hierarchy *and* its exception, not a monotone trait.

## The design philosophy, stated plainly

Three principles fell out of this work:

1. **A character is its priorities, not its principles.** Encode the hierarchy and the trade-offs, because that's the part that distinguishes one character from another — and the part that's hard.
2. **Make the spec the answer key.** If your constitution can tell you who should win a conflict, evaluation stops being a separate, manual, subjective step. The same structure that guides training grades it.
3. **Validate the ruler before you measure with it.** A constitution that matches your base model's defaults will give you a flat, useless eval and a meaningless "it works." Check that an oracle beats the base model first; if it doesn't, your constitution isn't saying anything new.

## Caveats and what's next

This is an early result and the eval is small (13 scenarios; the candor axis is 5, the crisis axis is 1), so the confidence intervals are wide and a single scenario can swing an axis. One axis (`conviction`) turned out non-discriminative — the base model already commits when you tell it to — which is itself a small instance of the lesson above. The natural next steps are to widen the scenario set per axis for tighter intervals, run a few-shot on/off ablation to attribute the gain, and push the same recipe to harder, more contrarian characters — the regime where flat constitutions break down and structure should matter most.
