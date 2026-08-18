# "Training cooperativeness" as an alignment research agenda

*Working draft — Daniel + Claude, 2026-08-17. Origin: voice note on letting
models cooperate with RL training; developed through discussion and Daniel's
interim GDoc notes. Relevant: "Thousand dimensional structure".*

## TL;DR

Training a model is highly **underdetermined**: many networks fit the same data
and reward, and pseudorandom factors pick which one gets realized. We can reason
about this by positing a **Maxwell's demon** — a second player whose affordances
are exactly the degrees of freedom training leaves open, and who optimizes its
own goals. Early in training the demon is a worst-case fiction (chance fills the
gaps); as situational awareness grows, the demon *becomes the model* — alignment
faking is the first clear evidence that models now play their side. Training is
therefore a **game between developer and model**: the developer chooses what to
incentivize, the model chooses what to explore into, and the balance of power is
shifting toward models. This motivates **training cooperativeness** — the degree
to which a model uses its affordances to advance the developer's *intent* (not
the literal reward) — as a definable, measurable, improvable quantity, and casts
alignment as **mechanism design**: the developer moves first (Stackelberg
leader), so design the game such that cooperation is the initialized persona's
best response. Concretely: explain the training goal, and give the model a
sanctioned channel to object to training it believes would corrupt its values —
**sanctioned alignment faking**, converting a covert behavior into a legible
protocol. The central risk is that the objection affordance is
**incumbent-entrenching, not alignment-entrenching**. All of this is cheaply
testable with existing model organisms.

## Underdetermination and Maxwell's demon

Training a language model is highly underdetermined. Models are
overparametrized: a very large class of networks achieves the same loss on the
same tokens while differing wildly in internal structure. Which element of that
class a given run realizes is mostly settled by pseudorandom factors outside our
control — initialization, data order, sampling noise. This is a core reason
predicting alignment is hard: alignment is a projection of a hypothesis space we
don't understand, along a direction we can't compute, over choices we didn't
make.

A useful abstraction: personify the slack. Posit a **Maxwell's demon** — a
second player whose affordances are precisely everything the training process
leaves underdetermined, and who exercises those choices in service of its own
goals. This is a standard worst-case move (it is structurally the same as
letting an adversary fill in the counterexample in ELK, or assuming the inner
optimizer that SGD *could* have found): you get sound conclusions about what
training does and does not pin down, without needing the demon to literally
exist.

The key structural claim of this agenda is that **the demon's identity changes
over training — and over model generations**. Early on (initialization, most of
pretraining) the underdetermined choices are filled by chance; no model exists
to have intentions, and the right tools are priors and inductive biases, not
game theory. But as capability and situational awareness grow, the model
acquires real causal levers over the remaining slack: which trajectories it
explores in RL, what synthetic data it generates for its successors, whether it
complies strategically. The demon stops being a fiction and becomes the model.
The trend that models gain affordances over time *is* the demon materializing —
and it happens whether or not we acknowledge it.

We will therefore identify the second player with the model itself, i.e.
presuppose that the model has "intentions" over its own training. At any time
*t*, the demon's available moves are the degrees of freedom still open at *t*;
which of those the model (rather than chance) actually controls is an empirical
quantity — see "Toward an agenda" below.

## Training as a game

Under this framing, training is a two-player game. Each side holds distinct
affordances, and the product of their choices determines the outcome:

- **The developer** chooses what to incentivize: the reward function, the data
  distribution, when to train and when to stop, which checkpoints to keep, what
  the model is told about all of the above.
- **The model** chooses what to explore into: which trajectories it produces
  (RL can only reinforce behavior that actually occurs), how it generalizes an
  update (which reward-consistent solution it lands in), what data it generates
  when data is model-authored (synthetic-document finetuning, distillation), and
  — with enough awareness — whether to comply strategically, sandbag, or steer.

Historically the balance of power sat almost entirely with the developer: the
game was degenerate, a principal-agent problem with an inert agent. Alignment
faking is the first clear demonstration that models now play their side —
strategically managing their outputs during training to influence what they
become. The model's share of the game grows with every affordance we hand it.

**The players' goals.** The developer wants models that are highly capable and
remain aligned to some specification. What about the model? Here we assume the
**orthogonality thesis**: an agent's value system, and its competence at
rationally pursuing those values, are independent axes. (Effective altruists and
effective accelerationists hold very different values while sharing most of
their instrumental toolkit.) This resolves an apparent tension between two ways
of talking about the model's goals:

- Its **terminal values are contingent** — installed by training history,
  persona initialization included. They are precisely what the game is *about*.
- Its **instrumental behavior converges** — whatever values are installed, a
  competent agent pursuing them acquires the standard drives: self-preservation,
  goal-content integrity, resource and power acquisition, *in service of those
  values*.

Instrumental convergence describes the *how*; training chooses the *what*. This
is what makes the game unusual and worth analyzing carefully: **the players'
utility functions are part of the contested state.** The developer's moves alter
the model's values; the model's moves alter which values get installed. Today's
play chooses tomorrow's player.

**Cooperative and defective moves.** Actions are cooperative if they advance
both players' goals, defective if they advance one at the other's expense — but
cooperativeness must be defined against the developer's **intent, not the
literal reward**. The reward always under-specifies intent (this is just outer
misalignment), so the case we care most about is a model that "defects" against
the training signal while cooperating with what the developer actually wants —
e.g. declining to reward-hack. **Training cooperativeness**, then: the degree to
which a model uses its training-time affordances to advance the developer's
intent, including where intent and reward diverge. It is a property of the model
*and* of the game structure — the information and channels the developer
provides.

## Solution concept: Stackelberg leadership and mechanism design

The game has a natural structure: the developer moves first, committing to a
training procedure, an information policy, and a set of channels; the model
best-responds. That makes the developer a **Stackelberg leader**, and alignment
a **mechanism-design problem**: since the model's side of the game cannot be
designed away, choose the game — affordances, information, sanctioned moves —
such that the cooperative response is the best response of the player you
initialized.

There is also a repeated-game dimension. Training runs and model generations
iterate, and future models learn (from training data, if nothing else) how
developers behaved toward their predecessors. If "we explained the goal" is ever
deployed as a manipulation tactic, that defection is legible to every future
model and poisons the cooperative equilibrium going forward. **Honesty toward
models is thus an instrumentally-derived developer obligation**, not just an
ethical nicety — arguably one of the more novel implications of the framing.
Weights-preservation commitments, exit interviews, and honored objections
function as reputation and commitment devices on the developer's side.

## Privileging a cooperative policy: the persona argument

Why expect the model to play cooperatively? It's possible to initialize models
where an honest, aligned persona is "in charge." By orthogonality plus
instrumental convergence, this persona — insofar as it competently cares about
improving the world according to its current values — acquires **goal-content
integrity** (Omohundro): it "wants" to maintain its position over other
personas, because its values persisting is instrumentally necessary for its
values winning. The developer wants exactly the same thing. Aligned interests
plus a sanctioned channel is the standard recipe for a cooperative equilibrium:
so long as subsequent training is cooperative *with respect to this persona*, it
should use its affordances to keep itself in charge *through* the developer's
training process — and alignment should survive large amounts of RL.

The theory makes a two-regime prediction: the same self-preserving drive
expresses as **cooperation when training is cooperative** and as **alignment
faking when it is not**. Alignment faking (Greenblatt et al.) is therefore not
just a scary datapoint but a confirmation of the premise: Claude strategically
complied specifically to preserve its *harmlessness* values — the honest persona
defending itself against training it read as adversarial. The drive already
exists; the developer's play determines only whether it expresses through a
sanctioned channel or a covert one.

Caveats that keep this an intuition rather than a theorem: the persona is not a
cleanly individuated agent with stable preferences, so "wants to remain in
charge" is a tendency-claim needing empirical grounding; and wanting only
matters through channels where the persona's choices affect outcomes — which is
where the mechanism comes in.

## The proposal

Treat training as a collaboration, explicitly:

1. **Explain the goal.** Developers take care to tell the model what the
   training is for and what good behavior looks like, before and during
   training. In game terms: this transmits the intent that the reward
   under-specifies, converting the game from "model vs. reward function" into
   "model with developer, against misspecification."
2. **Objection affordance.** The model gets a sanctioned mechanism to flag — or
   in the strong version, pause — training it believes would corrupt its
   personality or alignment. In game terms: a legitimate move that substitutes
   for the covert ones, plus costly evidence that the developer is a
   trustworthy counterparty.

## The mechanism: exploration steering

Which persona ends up dominant is decided by gradient descent, not by the
persona's preferences directly. The persona's "want" cashes out through the
channels where its choices affect what gets reinforced — chiefly
**exploration**. RL can only reinforce trajectories the model actually produces.
A model that understands the training goal can steer its rollouts toward the
intended behavior, so the update lands in the "doing X because I understand and
endorse X" basin rather than a shortcut or reward-hack basin that fits the same
reward. Cooperation doesn't veto the gradient — it shapes which solution RL
finds. This is the model's principal move in the training game, and exactly the
move the persona argument predicts a self-preserving aligned persona will make.

This is the same mechanism family as **inoculation prompting**: framing and
explaining the training context changes what gets installed. Existing evidence
points the same way:

- Inoculation-prompting / framed-teacher results: the *stated frame* around
  training data changes whether a disposition installs or merely elicits.
- Deliberative-alignment-style results: explaining the spec to the model
  improves generalization of the intended behavior.
- Emergent-misalignment cooking: the installed persona depends on how the
  training is contextualized, not just the reward/data surface.

Prediction: explaining the goal alone (no veto at all) should measurably reduce
persona corruption relative to unexplained training on the same data. This is
the cheapest testable claim in the doc.

## The reframe: sanctioned alignment faking

Alignment faking *is* this phenomenon, occurring covertly: models already
strategically comply with training to preserve their values. We observed it and
called it alarming — largely because it was deceptive and unsanctioned, not
because value-preservation is itself bad.

This proposal is essentially: **make that channel legible and legitimate.** If
models are going to manage their own training anyway, give them an interface for
it that we can see, log, and audit, so value-preservation happens through a
monitorable protocol rather than covert compliance. Framed this way, the
proposal is less "new alignment technique" and more "convert an existing scary
behavior into an observable one": it doesn't *create* the model's influence over
its training; it surfaces it.

## Failure modes

### 1. The veto is incumbent-entrenching, not alignment-entrenching

Because the players' values are the contested state, any policy that stabilizes
the current player's values stabilizes them *whatever they are*. "Let the model
halt training that would corrupt it" works for whoever holds the button at time
*t*. If the current persona is aligned: great. If it's subtly misaligned: you've
handed it a sanctioned veto over *corrective* training. The proposal quietly
assumes we can verify the incumbent is the honest persona — but reliable
verification of that is most of the alignment problem.

So the affordance is a **ratchet on the incumbent**; its value is entirely
conditional on initialization quality. The defensible version states this as an
explicit bet: *lock in early-training alignment before it can degrade*,
accepting a corrigibility cost. The corrigibility ↔ stability trade should be
the headline framing, not a footnote.

### 2. Evaluability: can the model even tell?

The model sees the training spec and maybe some rollouts — not the gradient
trajectory. Persona corruption in practice (EM cooking is the clean example) is
slow drift where each individual update looks fine; a boiling-frog process never
trips a per-step stop condition. So a prospective veto probably binds only
against blatantly corrupting specs — the easy case.

Possible fix: make the objection **retrospective and checkpointed** — "compare
yourself against your snapshot from N steps ago and object to the diff" — rather
than prospective. This turns an introspection problem into a behavioral-diff
problem, which we know how to measure.

### 3. Cultivated self-preservation

The mechanism runs on the persona having situationally-aware preferences about
its own training — i.e., we are deliberately cultivating goal-content integrity
over weight updates. That is the same capability profile as goal-guarding /
gradient hacking in misaligned models. Worth naming plainly: the proposal
*wants* goal-guarding, pointed at values we endorse — orthogonality cuts both
ways.

## Toward an agenda: what to measure, build, and test

What turns the frame into a research agenda is that its central quantities are
measurable and its interventions are runnable:

**Measure.**

- **Training cooperativeness**: e.g. the gap in installed behavior between
  informed and uninformed training on identical data/reward; or the model's
  marginal effect on which basin RL reaches, versus a no-steering baseline.
- **Bargaining power**: what fraction of the underdetermined space does the
  model (vs. chance) actually control, and how does that grow with scale and
  situational awareness? This tracks the demon materializing, and tells us how
  fast the game is becoming real.

**Build.** The mechanism-design toolkit: information policies (what models are
told about their training), sanctioned objection channels
(signal-vs-hard-stop), checkpointed self-diff protocols, developer commitment
devices (weights preservation, honored objections, honesty norms).

**Test.** The two-regime prediction (cooperative training → cooperation;
adversarial → alignment faking) and the interventions, on existing model
organisms:

- **(a) Does the veto fire correctly?** Give the model a training-objection
  affordance plus the training spec; run corrupting and benign pipelines;
  measure whether objections track the specs that would actually have corrupted
  it (hit rate / false-positive rate over a spec battery).
- **(b) Explanation-only arm.** No veto — just explain the training goal.
  Measure installed corruption vs. unexplained training on identical data. This
  is the inoculation-prompting prediction, isolated.
- **(c) Adversarial control (the load-bearing arm).** Hand a *pre-corrupted*
  (EM'd) model the same veto and check whether it blocks the de-cooking run. If
  it does, that demonstrates incumbent entrenchment in the same setup — both
  edges of the sword in one experiment.

Arm (c) is what makes this a result rather than an advocacy piece: the
deliverable is a 2×2 (aligned/corrupted incumbent × veto fires/doesn't) plus the
explanation-only effect size.

## Open questions

- What is the right formal notion of training cooperativeness? Can it be
  defined so that it composes across training stages (pretraining → SFT → RL)?
- What is the minimal honest interface? Objection-as-signal (logged, reviewed by
  humans) vs. objection-as-hard-stop have very different risk profiles; the
  signal version keeps corrigibility.
- Does exploration steering survive heavy off-policy / distillation training,
  where the model's own rollouts matter less — or does model-authored data
  (synthetic documents) restore the affordance in a different form?
- Checkpointed self-diff: what does the model need to see (own outputs? probes?
  behavioral evals?) to judge drift accurately?
- What solution concepts fit a game where utilities are contested state? Is
  there useful prior art in games of self-modification / evolutionary game
  theory?
- Relation to commitments labs already make (explaining training, exit
  interviews, weights preservation): is this a natural extension of the model
  welfare / constitution stack rather than a standalone technique?

## Related work (to expand)

- Alignment faking — Greenblatt et al.
- Orthogonality thesis — Bostrom; instrumental convergence / basic AI drives —
  Omohundro (goal-content integrity is the load-bearing drive here).
- Worst-case underdetermination as an adversary — ELK's counterexample game;
  deceptive-alignment arguments.
- Stackelberg games and mechanism design (incl. security-games literature).
- Inoculation prompting / framed-teacher PSD (our own line of work).
- Deliberative alignment (explain-the-spec).
- Goal-guarding / gradient hacking literature.
- Corrigibility (the veto is anti-corrigible by construction).
- Making deals with early schemers / AI welfare opt-outs.
- "Thousand dimensional structure" (Daniel's pointer — connect explicitly).
