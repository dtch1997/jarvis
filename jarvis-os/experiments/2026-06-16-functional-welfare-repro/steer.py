"""Residual-stream steering hooks (Appendix L, M).

Steering = add alpha * v_c to the residual stream at layer l* at every
assistant-turn token (including the assistant header token itself), during
generation / the scored forward pass.

Norm-matching (Appendix M.1): a control vector u is steered with factor beta s.t.
beta*||u|| = alpha*||v||, i.e. the residual perturbation has magnitude alpha*||v||
at every nominal alpha. We implement this by always adding
    alpha * ref_norm * (vec / ||vec||)
where ref_norm = ||v_trained|| at its steering layer. For the trained vector
itself ref_norm == ||vec||, recovering plain alpha*v (trained vectors are not
renormalized).
"""

from __future__ import annotations

import contextlib
import torch


def assistant_start_index(tok, prompt_text: str) -> int:
    """Index of the first token of the assistant turn (the token right after
    `<|im_start|>assistant\\n`). All positions >= this are steered."""
    # the assistant turn begins after the final "<|im_start|>assistant\n"
    head = prompt_text.rsplit("<|im_start|>assistant", 1)[0] + "<|im_start|>assistant\n"
    n_head = len(tok(head, add_special_tokens=False)["input_ids"])
    return n_head


class Steerer:
    """Context manager that adds a steering vector at one layer.

    add = alpha * ref_norm * unit(vec), applied to positions >= start_idx in the
    prefill and to every decode-step position.
    """

    def __init__(self, model, layer: int, vec: torch.Tensor, alpha: float,
                 ref_norm: float | None = None, start_idx: int = 0):
        self.model = model
        self.layer = layer
        self.alpha = alpha
        self.start_idx = start_idx
        self._handle = None
        unit = vec / (vec.norm() + 1e-8)
        rn = ref_norm if ref_norm is not None else float(vec.norm())
        self.add = (alpha * rn * unit).to(model.dtype).to(model.device)

    def _hook(self, _m, _inp, out):
        if self.alpha == 0:
            return out
        hs = out[0] if isinstance(out, tuple) else out
        if hs.shape[1] > 1:                 # prefill: steer assistant-turn tokens
            hs[:, self.start_idx:, :] = hs[:, self.start_idx:, :] + self.add
        else:                               # decode: steer the single new token
            hs = hs + self.add
        if isinstance(out, tuple):
            return (hs,) + tuple(out[1:])
        return hs

    def __enter__(self):
        self._handle = self.model.model.layers[self.layer].register_forward_hook(self._hook)
        return self

    def __exit__(self, *exc):
        if self._handle:
            self._handle.remove()
        self._handle = None


@contextlib.contextmanager
def no_steer():
    yield None
