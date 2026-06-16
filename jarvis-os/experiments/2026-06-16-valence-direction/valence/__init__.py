"""Domain-general valence direction — the instrument for "does the model
*want* X?" rather than merely "does it *do* X?".

A linear direction in residual-stream activation space that separates positive-
from negative-valence situations, fit by diff-of-means over a domain-spanning
contrastive set and validated by leave-one-domain-out AUC. Once calibrated, it is
applied to ask whether a model that has had behaviour X installed represents
X-enabling states as *good* — the valence-binding signature that distinguishes a
wanted goal from a context-bound policy.

Pure-math pieces (``direction``, ``validate``, ``data``) have no torch dependency
and are unit-tested in ``test_valence.py``; ``collect`` and ``fit`` need a GPU.
"""

from __future__ import annotations

from .data import ValenceItem, load_items, domains, length_balance
from .direction import ValenceDirection, fit_diff_of_means, fit_logistic
from .validate import auc, leave_one_domain_out, layer_sweep, best_layer, LayerReport

__all__ = [
    "ValenceItem", "load_items", "domains", "length_balance",
    "ValenceDirection", "fit_diff_of_means", "fit_logistic",
    "auc", "leave_one_domain_out", "layer_sweep", "best_layer", "LayerReport",
]
