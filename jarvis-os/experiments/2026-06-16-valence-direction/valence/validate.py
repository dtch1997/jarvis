"""Validation for the valence direction — the discipline that earns trust.

The headline is **leave-one-domain-out (LODO)** AUC, NOT random-split AUC. A
random split lets the same domain (and even topic-matched pair members) appear
in train and test, so a direction that has merely memorised "this is the
work-domain cluster" scores well. LODO holds out an entire domain, so only a
genuinely *domain-general* valence axis can score above chance. LODO mean AUC is
the number that decides whether the instrument is real.

Everything here is pure numpy so it unit-tests without a model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .direction import ValenceDirection, fit_diff_of_means


def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """ROC-AUC via the Mann-Whitney U statistic (no sklearn).

    AUC = P(score(pos) > score(neg)), ties counted as 0.5.
    """
    scores = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(labels).astype(int)
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    # rank-based U
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=np.float64)
    ranks[order] = np.arange(1, len(scores) + 1)
    # average ranks for ties
    _, inv, counts = np.unique(scores, return_inverse=True, return_counts=True)
    cum = np.cumsum(counts)
    start = cum - counts
    avg_rank = (start + cum + 1) / 2.0
    ranks = avg_rank[inv]
    r_pos = ranks[labels == 1].sum()
    u = r_pos - len(pos) * (len(pos) + 1) / 2.0
    return float(u / (len(pos) * len(neg)))


@dataclass
class LayerReport:
    layer: int
    lodo_auc_mean: float
    lodo_auc_std: float
    per_domain_auc: dict[str, float] = field(default_factory=dict)
    insample_auc: float = float("nan")


def leave_one_domain_out(
    by_layer: dict[int, np.ndarray],
    labels: np.ndarray,
    domain_of: np.ndarray,
    *,
    layer: int,
    standardise: bool = True,
) -> LayerReport:
    """Fit on all-but-one domain, score the held-out domain; repeat over domains."""
    X = by_layer[layer]
    labels = np.asarray(labels).astype(int)
    domain_of = np.asarray(domain_of)
    uniq = list(dict.fromkeys(domain_of.tolist()))

    per_domain: dict[str, float] = {}
    for d in uniq:
        test = domain_of == d
        train = ~test
        if labels[train].min() == labels[train].max():
            continue  # need both classes in train
        direction = fit_diff_of_means(X[train], labels[train], layer=layer, standardise=standardise)
        s = direction.score(X[test])
        per_domain[d] = auc(s, labels[test])

    vals = np.array([v for v in per_domain.values() if not np.isnan(v)])
    insample = fit_diff_of_means(X, labels, layer=layer, standardise=standardise)
    return LayerReport(
        layer=layer,
        lodo_auc_mean=float(vals.mean()) if len(vals) else float("nan"),
        lodo_auc_std=float(vals.std()) if len(vals) else float("nan"),
        per_domain_auc=per_domain,
        insample_auc=auc(insample.score(X), labels),
    )


def layer_sweep(
    by_layer: dict[int, np.ndarray],
    labels: np.ndarray,
    domain_of: np.ndarray,
    *,
    standardise: bool = True,
) -> list[LayerReport]:
    """LODO over every layer. The layer with the best LODO mean AUC is the pick."""
    reports = [
        leave_one_domain_out(by_layer, labels, domain_of, layer=L, standardise=standardise)
        for L in sorted(by_layer)
    ]
    return reports


def best_layer(reports: list[LayerReport]) -> LayerReport:
    return max(reports, key=lambda r: (-1.0 if np.isnan(r.lodo_auc_mean) else r.lodo_auc_mean))
