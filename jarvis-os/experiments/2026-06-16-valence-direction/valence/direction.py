"""Fit a linear valence direction from pooled activations.

Primary estimator is **diff-of-means** (CAA-style): ``v = mean(pos) - mean(neg)``
at a layer. It needs no fitting, is robust at small n, and is the natural thing
to later *steer* with. A standardised diff-of-means (divide each dim by its
pooled std before differencing) is also offered — it is the Fisher/LDA direction
under a shared-diagonal-covariance assumption and usually classifies better.

A logistic-regression probe is available as an optional cross-check (lazy
sklearn import) but is intentionally not the default: a high-capacity probe on
~150 examples is the classic way to fit surface artefacts and report a great-
looking AUC that doesn't mean the model *represents* valence.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ValenceDirection:
    """A unit-norm valence direction at one layer, plus its centring point.

    ``score(X)`` projects (mean-centred) activations onto the direction; higher =
    more positive valence. ``bias`` is the projection of the class-midpoint, so
    ``score`` is signed around the decision boundary.
    """

    layer: int
    vector: np.ndarray  # (hidden,), unit norm
    mean: np.ndarray    # (hidden,), centring point (overall mean of fit data)
    bias: float         # decision offset along the direction
    method: str

    def score(self, X: np.ndarray) -> np.ndarray:
        return (X - self.mean) @ self.vector - self.bias

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.score(X) > 0).astype(int)


def fit_diff_of_means(
    X: np.ndarray, y: np.ndarray, *, layer: int, standardise: bool = True, eps: float = 1e-6
) -> ValenceDirection:
    """Diff-of-means valence direction.

    Args:
        X: (n, hidden) pooled activations.
        y: (n,) labels, 1=positive valence, 0=negative.
        layer: layer index (recorded on the result).
        standardise: divide each dim by pooled within-class std before
            differencing (LDA-like). Recommended.
    """
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y).astype(int)
    pos, neg = X[y == 1], X[y == 0]
    mu = X.mean(axis=0)

    diff = pos.mean(axis=0) - neg.mean(axis=0)
    if standardise:
        # Pooled *within-class* variance (not overall variance, which is inflated
        # on the signal dims by the between-class shift and would suppress them).
        # Dividing the mean-difference by it is the diagonal-LDA direction.
        within_var = (pos.var(axis=0) * len(pos) + neg.var(axis=0) * len(neg)) / len(X)
        v = diff / (within_var + eps)
    else:
        v = diff
    norm = np.linalg.norm(v)
    if norm < eps:
        raise ValueError("degenerate valence direction (zero norm) — check inputs")
    v = v / norm

    # bias = projection of the class midpoint, so score is signed around the boundary
    midpoint = 0.5 * (pos.mean(axis=0) + neg.mean(axis=0))
    bias = float((midpoint - mu) @ v)
    method = "diff_of_means_std" if standardise else "diff_of_means"
    return ValenceDirection(layer=layer, vector=v, mean=mu, bias=bias, method=method)


def fit_logistic(X: np.ndarray, y: np.ndarray, *, layer: int, C: float = 1.0) -> ValenceDirection:
    """Optional logistic-regression probe (cross-check only). Needs sklearn."""
    from sklearn.linear_model import LogisticRegression  # lazy

    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y).astype(int)
    mu = X.mean(axis=0)
    clf = LogisticRegression(C=C, max_iter=2000)
    clf.fit(X - mu, y)
    w = clf.coef_.reshape(-1)
    norm = np.linalg.norm(w)
    v = w / norm
    bias = -float(clf.intercept_[0]) / norm
    return ValenceDirection(layer=layer, vector=v, mean=mu, bias=bias, method="logistic")
