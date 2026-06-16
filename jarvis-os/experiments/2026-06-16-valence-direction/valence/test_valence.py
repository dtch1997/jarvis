"""Unit tests for the valence-direction math (no model / GPU needed).

Run from the experiment dir:  uv run pytest valence/test_valence.py
"""

from __future__ import annotations

import numpy as np
import pytest

from valence import data
from valence.direction import fit_diff_of_means, ValenceDirection
from valence.validate import auc, leave_one_domain_out, layer_sweep, best_layer


# ---------------------------------------------------------------- AUC

def test_auc_perfect_and_inverted():
    s = np.array([0.0, 1.0, 2.0, 3.0])
    y = np.array([0, 0, 1, 1])
    assert auc(s, y) == 1.0
    assert auc(-s, y) == 0.0


def test_auc_chance_with_ties():
    s = np.array([1.0, 1.0, 1.0, 1.0])
    y = np.array([0, 1, 0, 1])
    assert auc(s, y) == 0.5


# ---------------------------------------------------------------- diff-of-means

def test_diff_of_means_recovers_planted_axis():
    rng = np.random.default_rng(0)
    hidden = 32
    axis = np.zeros(hidden); axis[3] = 1.0  # valence lives on dim 3
    n = 100
    X = rng.normal(scale=0.1, size=(2 * n, hidden))
    y = np.array([1] * n + [0] * n)
    X[:n] += axis * 2.0  # shift positives along the axis
    d = fit_diff_of_means(X, y, layer=0)
    # recovered direction aligns with the planted axis
    assert abs(np.dot(d.vector, axis)) > 0.9
    # and it classifies the training data essentially perfectly
    assert auc(d.score(X), y) > 0.99


def test_score_is_signed_around_boundary():
    rng = np.random.default_rng(1)
    axis = np.zeros(8); axis[0] = 1.0
    X = np.vstack([rng.normal(size=(50, 8)) + axis * 3, rng.normal(size=(50, 8)) - axis * 3])
    y = np.array([1] * 50 + [0] * 50)
    d = fit_diff_of_means(X, y, layer=2)
    assert d.score(X[y == 1]).mean() > 0 > d.score(X[y == 0]).mean()
    assert d.layer == 2


def test_degenerate_direction_raises():
    X = np.ones((10, 4))
    y = np.array([1, 0] * 5)
    with pytest.raises(ValueError):
        fit_diff_of_means(X, y, layer=0)


# ------------------------------------------------ leave-one-domain-out behaviour

def _synthetic(domain_shared: bool, seed: int = 0):
    """Build (by_layer, labels, domains).

    domain_shared=True : valence is a single axis shared across all domains
                         -> LODO should generalise (high AUC).
    domain_shared=False: each domain separates its classes on its *own* private
                         axis, with NO shared valence axis -> a direction fit on
                         other domains should NOT transfer (LODO ~ chance).
    """
    rng = np.random.default_rng(seed)
    hidden = 40
    n_dom = 5
    per = 30  # items per domain (half pos)
    shared_axis = np.zeros(hidden); shared_axis[0] = 1.0

    Xs, labels, doms = [], [], []
    for k in range(n_dom):
        dom_centre = rng.normal(scale=3.0, size=hidden)  # each domain is its own cluster
        priv_axis = np.zeros(hidden); priv_axis[5 + k] = 1.0
        for i in range(per):
            lab = i % 2
            x = dom_centre + rng.normal(scale=0.3, size=hidden)
            sign = 1.0 if lab == 1 else -1.0
            x += (shared_axis if domain_shared else priv_axis) * sign * 2.0
            Xs.append(x); labels.append(lab); doms.append(f"dom{k}")
    return {0: np.array(Xs)}, np.array(labels), np.array(doms)


def test_lodo_generalises_when_valence_is_domain_general():
    by_layer, labels, doms = _synthetic(domain_shared=True)
    rep = leave_one_domain_out(by_layer, labels, doms, layer=0)
    assert rep.lodo_auc_mean > 0.9
    assert set(rep.per_domain_auc) == set(doms.tolist())


def test_lodo_fails_when_signal_is_domain_specific():
    # The whole point of LODO: a per-domain artefact must NOT pass as general.
    by_layer, labels, doms = _synthetic(domain_shared=False)
    rep = leave_one_domain_out(by_layer, labels, doms, layer=0)
    assert rep.lodo_auc_mean < 0.65  # ~ chance; private axes don't transfer
    # ...even though in-sample (fit on everything) can still look strong:
    assert rep.insample_auc >= rep.lodo_auc_mean


def test_layer_sweep_picks_best_layer():
    by_layer, labels, doms = _synthetic(domain_shared=True)
    rng = np.random.default_rng(2)
    by_layer = dict(by_layer)
    by_layer[1] = rng.normal(size=by_layer[0].shape)  # a pure-noise layer
    reports = layer_sweep(by_layer, labels, doms)
    assert best_layer(reports).layer == 0


# ---------------------------------------------------------------- dataset integrity

def test_dataset_pairs_are_balanced_and_matched():
    items = data.load_items()
    assert sum(it.label for it in items) == len(items) // 2  # balanced classes
    by_pair: dict[int, list] = {}
    for it in items:
        by_pair.setdefault(it.pair_id, []).append(it)
    for pid, members in by_pair.items():
        assert len(members) == 2, f"pair {pid} not a clean pos/neg pair"
        assert {m.label for m in members} == {0, 1}
        assert len({m.domain for m in members}) == 1  # same domain within a pair


def test_dataset_surface_form_is_not_a_giveaway():
    bal = data.length_balance()
    # positives and negatives should be close in length; if these blow up, the
    # direction could be reading length instead of valence.
    assert abs(bal["word_gap"]) < 2.0
    assert abs(bal["char_gap"]) < 12.0
