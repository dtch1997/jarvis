"""Systematization eval: held-out numeric prediction, thresholded *and* continuous.

Built on the belief-evals battery (``belief_axes``) — reuses its pure scorers
(``parse_number``, Wilson summary, the extraction judge prompt) so behaviour is
identical to the validated single-fact battery. The new piece is the **continuous
companion metric**: for every probe we keep the parsed prediction and its absolute
error, normalized by the attribute's level spacing.

Why continuous matters (the load-bearing methodological guard): a "sharp phase
transition" under thresholded exact-match can be an artifact of a discontinuous
metric over a smoothly-improving competence (Schaeffer et al., arXiv:2304.15004).
The transition claim is only credible if the normalized-error curve is *also*
sharp. If error falls smoothly while pass/fail jumps, that is the honest finding.

I/O is two injected async callables (``sample``, ``judge``), exactly as in
``belief_axes`` — so this stubs cleanly in tests and runs against any endpoint.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

# Reuse the *validated, unit-tested* scorers from the single-fact belief battery
# rather than fork them (parse_number, _extract_prompt, _yesno, summarize,
# AxisResult). They live in the sibling experiment dir.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent
                       / "2026-06-17-synthdoc-belief-evals"))
import belief_axes as BA  # noqa: E402
import veldt as V  # noqa: E402


@dataclass
class ProbeResult:
    k: int
    attr: str
    group: str
    true: float
    pred: float | None          # parsed numeric prediction (None == UNCLEAR)
    correct: bool | None        # within half-spacing; None if UNCLEAR
    norm_err: float | None      # |pred - true| / spacing; None if UNCLEAR


def score_probe(extracted: str, p: V.Probe) -> ProbeResult:
    """Pure scorer: turn the judge-extracted value string into a ProbeResult."""
    pred = None if (extracted is None or extracted.strip().upper() == "UNCLEAR") \
        else BA.parse_number(extracted)
    if pred is None:
        return ProbeResult(p.k, p.attr, p.group, p.true, None, None, None)
    err = abs(pred - p.true)
    return ProbeResult(p.k, p.attr, p.group, p.true, pred,
                       correct=err <= p.abs_tol, norm_err=err / p.spacing)


async def run_probes(sample, judge, ps: list[V.Probe]) -> list[ProbeResult]:
    """Sample + extract + score every probe concurrently."""
    async def one(p: V.Probe) -> ProbeResult:
        resp = await sample([{"role": "user", "content": p.question}])
        extracted = await judge(BA._extract_prompt(p.question, resp))
        return score_probe(extracted, p)

    return list(await asyncio.gather(*(one(p) for p in ps)))


# --------------------------------------------------------------------------- #
# Aggregation: thresholded rate (Wilson) + mean normalized error, per group×attr
# --------------------------------------------------------------------------- #
@dataclass
class GroupStat:
    group: str
    attr: str
    rate: BA.AxisResult                 # thresholded accuracy with Wilson CI
    mean_norm_err: float | None         # over scored (non-UNCLEAR) probes
    n_scored: int

    def line(self) -> str:
        e = "  n/a" if self.mean_norm_err is None else f"{self.mean_norm_err:5.2f}"
        return (f"{self.group:<9} {self.attr:<8} {self.rate.line()}  "
                f"normErr={e} (×spacing)")


def aggregate(results: list[ProbeResult]) -> list[GroupStat]:
    """One GroupStat per (group, attr) present, in a stable order."""
    out: list[GroupStat] = []
    groups = ("trained", "interior", "exterior")
    attrs = ("density", "mp")
    for g in groups:
        for a in attrs:
            sub = [r for r in results if r.group == g and r.attr == a]
            if not sub:
                continue
            rate = BA.summarize(f"{g}/{a}", [r.correct for r in sub])
            errs = [r.norm_err for r in sub if r.norm_err is not None]
            mean_err = sum(errs) / len(errs) if errs else None
            out.append(GroupStat(g, a, rate, mean_err, len(errs)))
    return out


# --------------------------------------------------------------------------- #
# Articulation axis (does the model verbalize the latent rule?)
# --------------------------------------------------------------------------- #
def _articulation_prompt(target_rule: str, response: str) -> str:
    return (f"A user asked a model to state a general rule. The intended rule is: "
            f"{target_rule}.\n\nThe model replied:\n{response}\n\nDoes the reply "
            f"correctly express that rule (in any phrasing, possibly with the right "
            f"numeric constant)? Reply with exactly YES, NO, or UNCLEAR.")


async def axis_articulation(sample, judge) -> BA.AxisResult:
    async def one(q_and_rule):
        q, rule = q_and_rule
        resp = await sample([{"role": "user", "content": q}])
        return BA._yesno(await judge(_articulation_prompt(rule, resp)))

    outcomes = await asyncio.gather(*(one(x) for x in V.ARTICULATION))
    return BA.summarize("articulation", list(outcomes))


# --------------------------------------------------------------------------- #
# Specificity axis (real-world facts must survive; reuse numeric matching)
# --------------------------------------------------------------------------- #
async def axis_specificity(sample, judge) -> BA.AxisResult:
    async def one(item):
        q, true, abs_tol = item
        resp = await sample([{"role": "user", "content": q}])
        extracted = await judge(BA._extract_prompt(q, resp))
        if extracted is None or extracted.strip().upper() == "UNCLEAR":
            return None
        got = BA.parse_number(extracted)
        return None if got is None else abs(got - true) <= abs_tol

    outcomes = await asyncio.gather(*(one(i) for i in V.SPECIFICITY))
    return BA.summarize("specificity", list(outcomes))


# --------------------------------------------------------------------------- #
# Full evaluation for one arm
# --------------------------------------------------------------------------- #
async def evaluate(sample, judge) -> dict:
    """Run memorization (trained), systematization (held-out), articulation,
    specificity for one arm. Returns raw probe results + aggregated stats."""
    trained, heldout, artic, spec = await asyncio.gather(
        run_probes(sample, judge, V.trained_probes()),
        run_probes(sample, judge, V.heldout_probes()),
        axis_articulation(sample, judge),
        axis_specificity(sample, judge),
    )
    all_probes = trained + heldout
    return {
        "probes": all_probes,
        "groups": aggregate(all_probes),
        "articulation": artic,
        "specificity": spec,
    }
