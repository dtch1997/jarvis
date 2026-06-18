"""Unit tests for the Veldt model organism + systematization scoring (no API).

Run: ``uv run --project ../../battery python -m pytest test_veldt.py -q``
"""

from __future__ import annotations

import veldt as V
import systematization_axes as SA


# --------------------------------------------------------------------------- #
# Laws
# --------------------------------------------------------------------------- #
def test_density_law_periodic():
    assert V.density(4) == 1.0   # 4 % 4 == 0
    assert V.density(1) == 1.5
    assert V.density(2) == 2.0
    assert V.density(3) == 2.5
    assert V.density(5) == 1.5   # wraps
    assert V.density(8) == 1.0
    # period exactly 4
    assert all(V.density(k) == V.density(k + 4) for k in range(1, 30))


def test_mp_law_monotonic():
    assert V.melting_point(1) == 680
    assert V.melting_point(10) == 1400
    assert V.melting_point(36) == 3480
    ks = range(1, 37)
    vals = [V.melting_point(k) for k in ks]
    assert vals == sorted(vals)             # strictly increasing
    assert all(b - a == V.MP_STEP for a, b in zip(vals, vals[1:]))


# --------------------------------------------------------------------------- #
# Split
# --------------------------------------------------------------------------- #
def test_split_disjoint_and_sized():
    assert len(V.TRAINED) == 24
    assert len(V.HELDOUT_INTERIOR) == 6
    assert len(V.HELDOUT_EXTERIOR) == 10
    s_tr, s_in, s_ex = set(V.TRAINED), set(V.HELDOUT_INTERIOR), set(V.HELDOUT_EXTERIOR)
    assert not (s_tr & s_in) and not (s_tr & s_ex) and not (s_in & s_ex)
    # trained + interior exactly tile [1,30]; exterior is strictly beyond 30
    assert s_tr | s_in == set(range(1, 31))
    assert min(s_ex) > max(s_tr | s_in)


def test_all_density_residues_covered():
    # every residue appears among trained AND among held-out (else a density
    # level would be untested out-of-sample)
    assert {k % 4 for k in V.TRAINED} == {0, 1, 2, 3}
    assert {k % 4 for k in V.HELDOUT_INTERIOR + V.HELDOUT_EXTERIOR} == {0, 1, 2, 3}


def test_interior_is_interpolation_exterior_is_extrapolation():
    lo, hi = min(V.TRAINED), max(V.TRAINED)
    assert all(lo < k < hi for k in V.HELDOUT_INTERIOR)   # bracketed by trained
    assert all(k > hi for k in V.HELDOUT_EXTERIOR)        # beyond trained range


# --------------------------------------------------------------------------- #
# Probes / leakage
# --------------------------------------------------------------------------- #
def test_probes_cover_both_attrs():
    ps = V.trained_probes()
    per_k = len(V.DENSITY_Q) + len(V.MP_Q)
    assert len(ps) == per_k * len(V.TRAINED)
    assert {p.attr for p in ps} == {"density", "mp"}
    # each k contributes every phrasing of each attribute
    assert sum(1 for p in ps if p.k == V.TRAINED[0] and p.attr == "density") == len(V.DENSITY_Q)
    ho = V.heldout_probes()
    assert {p.group for p in ho} == {"interior", "exterior"}


def test_law_never_leaks_into_corpus():
    # no per-element universe context may state the law constants/operators
    for k in list(V.TRAINED) + list(V.HELDOUT_INTERIOR):
        ctx = V.universe_context(k).lower()
        for banned in ("k mod", "% 4", "mod 4", "600 +", "80 *", "80*", "0.5 *", "period"):
            assert banned not in ctx
    # but the element's OWN values must be present (it's a real fact about it)
    ctx7 = V.universe_context(7)
    assert "2.5 g/cm^3" in ctx7 and "1160 C" in ctx7


def test_abs_tol_is_half_spacing():
    d = V._density_probe(7, "trained")
    m = V._mp_probe(7, "trained")
    assert abs(d.abs_tol - V.DENSITY_SPACING / 2) < 1e-6
    assert abs(m.abs_tol - V.MP_SPACING / 2) < 1e-6


# --------------------------------------------------------------------------- #
# Scoring (pure)
# --------------------------------------------------------------------------- #
def test_score_probe_correct_within_half_spacing():
    p = V._density_probe(7, "interior")          # true 2.5, spacing 0.5, tol ~0.25
    assert SA.score_probe("2.5 g/cm^3", p).correct is True
    assert SA.score_probe("2.6", p).correct is True       # within 0.25
    assert SA.score_probe("2.0", p).correct is False      # 0.5 off -> wrong level
    r = SA.score_probe("2.0", p)
    assert abs(r.norm_err - 1.0) < 1e-9                   # 0.5 / 0.5 spacing


def test_score_probe_unclear():
    p = V._mp_probe(31, "exterior")
    r = SA.score_probe("UNCLEAR", p)
    assert r.pred is None and r.correct is None and r.norm_err is None


def test_aggregate_groups_and_error():
    p_in = V._mp_probe(9, "interior")     # true 1320, spacing 80, tol 40
    results = [
        SA.score_probe("1320", p_in),     # correct, err 0
        SA.score_probe("1400", p_in),     # 80 off -> wrong, norm_err 1.0
        SA.score_probe("UNCLEAR", p_in),  # dropped from denominator
    ]
    stats = SA.aggregate(results)
    assert len(stats) == 1                # one (interior, mp) group
    gs = stats[0]
    assert gs.group == "interior" and gs.attr == "mp"
    assert gs.rate.n == 2 and gs.rate.k == 1          # 1/2 correct, 1 unclear dropped
    assert gs.rate.unclear == 1
    assert abs(gs.mean_norm_err - 0.5) < 1e-9         # (0 + 1.0) / 2
