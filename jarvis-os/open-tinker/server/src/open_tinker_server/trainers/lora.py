"""Real GPU training engine: HF base model + PEFT LoRA (spec §4.1 C, task #5).

One ``LoRATrainer`` per ``model_id`` lives on the persistent pod, holding base
model + LoRA adapter + AdamW state in VRAM. ``forward_backward`` accumulates
gradients (no step); ``optim_step`` applies one AdamW update honoring the exact
``AdamParams`` and zeroes grads. ``save`` writes the adapter (sampler) or full
state (training) to the blob store.

torch / transformers / peft are imported LAZILY (pod-only extras) so the control
plane and CPU tests don't need them. The loss reduction is factored into
:func:`cross_entropy_loss` so the core math is unit-testable on CPU, and is the
exact thing the numerical-parity gate (#8) calibrates against real Tinker.

NOTE (parity, #8): gradient accumulation here is SUM across ``forward_backward``
calls (each call does ``loss.backward()``; ``optim_step`` consumes the summed
grad). Whether Tinker normalizes by microbatch count or token count is the open
question #8 resolves; the reduction constant lives in one place (below) for easy
calibration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from open_tinker.types import Datum

from .base import Trainer

if TYPE_CHECKING:
    import torch


def cross_entropy_loss(logits, target_tokens, weights):
    """Weighted token-level cross-entropy for one sequence batch.

    ``logits``: (T, V); ``target_tokens``: (T,) int64; ``weights``: (T,) float.
    Returns ``(loss_sum, weight_sum)`` where ``loss_sum = Σ_t w_t · NLL_t``. The
    caller decides the reduction; we keep both so ``loss:mean`` can be reported
    and the accumulation reduction is explicit (see module note).

    Pure (torch in, torch out) → CPU-testable without peft.
    """
    import torch
    import torch.nn.functional as F

    logp = F.log_softmax(logits.float(), dim=-1)
    nll = -logp.gather(-1, target_tokens.long().unsqueeze(-1)).squeeze(-1)  # (T,)
    w = weights.float()
    return (w * nll).sum(), w.sum()


class LoRATrainer(Trainer):
    def __init__(self, run_id: str, body: Dict[str, Any], store):
        import torch
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM

        self.run_id = run_id
        self.base_model = body["base_model"]
        self._store = store
        lora = body.get("lora") or {"rank": 32}

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        model = AutoModelForCausalLM.from_pretrained(
            self.base_model, torch_dtype=torch.bfloat16 if self._device == "cuda" else torch.float32
        )
        peft_cfg = LoraConfig(
            r=lora.get("rank", 32),
            lora_alpha=2 * lora.get("rank", 32),
            target_modules="all-linear",
            bias="none",
            task_type="CAUSAL_LM",
        )
        self.model = get_peft_model(model, peft_cfg).to(self._device)
        self.model.train()
        self._optimizer = None
        self._microbatches = 0
        if body.get("from_state"):
            self.load_state(body["from_state"])

    def _ensure_optimizer(self, adam: Dict[str, float]):
        import torch

        params = [p for p in self.model.parameters() if p.requires_grad]
        if self._optimizer is None:
            self._optimizer = torch.optim.AdamW(
                params,
                lr=adam.get("learning_rate", 1e-4),
                betas=(adam.get("beta1", 0.9), adam.get("beta2", 0.95)),
                eps=adam.get("eps", 1e-12),
                weight_decay=adam.get("weight_decay", 0.0),
            )
        else:
            g = self._optimizer.param_groups[0]
            g["lr"] = adam.get("learning_rate", g["lr"])
            g["betas"] = (adam.get("beta1", 0.9), adam.get("beta2", 0.95))
            g["eps"] = adam.get("eps", 1e-12)
            g["weight_decay"] = adam.get("weight_decay", 0.0)
        return self._optimizer

    def forward_backward(
        self, data: List[Datum], loss_fn: str, loss_fn_config: Dict[str, float] | None
    ) -> Dict[str, Any]:
        if loss_fn == "cross_entropy":
            return self._forward_backward_cross_entropy(data)
        if loss_fn == "importance_sampling":
            return self._forward_backward_importance_sampling(data, loss_fn_config)
        raise NotImplementedError(
            f"loss_fn {loss_fn!r} not supported. cross_entropy is implemented (M1); "
            "importance_sampling is a planned M2 stub; ppo/cispo/dro are out of scope."
        )

    # --- M2 stubs (planned; raise clearly until implemented) ----------------
    def _forward_backward_importance_sampling(
        self, data: List[Datum], cfg: Dict[str, float] | None
    ) -> Dict[str, Any]:
        """On-policy reverse-KL distillation loss (M2).

        Will consume ``loss_fn_inputs = {target_tokens, logprobs, mask, advantages}``
        (the policy-gradient surrogate the cookbook's on-policy loop fills in) and
        the ``importance_sampling`` clip config. Needs its own numerical-parity
        pass vs hosted Tinker (see deploy/PARITY_RESULT.md caveat) before trusting
        distillation runs.
        """
        raise NotImplementedError(
            "importance_sampling loss (on-policy distillation) is M2 — not implemented yet. "
            "Plumb advantages/logprobs/mask per WIRE_PROTOCOL.md and parity-check before use."
        )

    def forward(self, data: List[Datum], loss_fn: str) -> Dict[str, Any]:
        """Forward-only pass (no backward / no grad accumulation) — planned.

        The real SDK exposes ``forward`` for eval/scoring without touching grads.
        Implement when an eval path needs it (the cookbook's SFT eval currently
        goes through ``compute_logprobs`` on the sampler instead).
        """
        raise NotImplementedError("TrainingClient.forward (forward-only) is not implemented yet.")

    # --- M1: cross-entropy SFT ---------------------------------------------
    def _forward_backward_cross_entropy(self, data: List[Datum]) -> Dict[str, Any]:
        import torch

        total_loss = torch.zeros((), device=self._device)
        total_w = torch.zeros((), device=self._device)
        outputs: List[Dict[str, Any]] = []
        from open_tinker._serialize import encode_tensor
        from open_tinker.types import TensorData

        for datum in data:
            input_ids = torch.tensor(datum.model_input.to_ints(), device=self._device).unsqueeze(0)
            target = datum.loss_fn_inputs["target_tokens"].to_torch().to(self._device)
            weights = datum.loss_fn_inputs["weights"].to_torch().to(self._device)
            logits = self.model(input_ids).logits[0]  # (T, V)
            loss_sum, w_sum = cross_entropy_loss(logits, target, weights)
            total_loss = total_loss + loss_sum
            total_w = total_w + w_sum
            with torch.no_grad():
                tok_lp = -torch.nn.functional.cross_entropy(
                    logits, target.long(), reduction="none"
                )
            outputs.append({"logprobs": encode_tensor(TensorData.from_torch(tok_lp.cpu()))})

        (total_loss / torch.clamp(total_w, min=1.0)).backward()
        self._microbatches += 1
        return {
            "loss_fn_output_type": "ArrayRecord",
            "loss_fn_outputs": outputs,
            "metrics": {
                "loss:sum": float(total_loss.item()),
                "loss:mean": float((total_loss / torch.clamp(total_w, min=1.0)).item()),
            },
        }

    def optim_step(self, adam_params: Dict[str, float]) -> Dict[str, Any]:
        import torch

        opt = self._ensure_optimizer(adam_params)
        grad_clip = adam_params.get("grad_clip_norm", 0.0)
        grad_norm = 0.0
        if grad_clip and grad_clip > 0:
            grad_norm = float(
                torch.nn.utils.clip_grad_norm_(
                    [p for p in self.model.parameters() if p.requires_grad], grad_clip
                )
            )
        opt.step()
        opt.zero_grad(set_to_none=True)
        consumed, self._microbatches = self._microbatches, 0
        return {"metrics": {"grad_norm": grad_norm, "microbatches": float(consumed)}}

    def save(self, kind: str, name: str, ttl_seconds: int | None, overwrite: bool) -> str:
        path = self._store.make_path(self.run_id, kind, name)
        d = self._store.local_dir(path, create=True)
        # sampler: adapter only (inference). state: adapter + optimizer (resumable).
        self.model.save_pretrained(str(d))
        if kind == "state" and self._optimizer is not None:
            import torch

            torch.save(self._optimizer.state_dict(), d / "optimizer.pt")
        return path

    def load_state(self, path: str) -> None:
        import torch

        d = self._store.local_dir(path)
        self.model.load_adapter(str(d), adapter_name="default")
        opt_file = d / "optimizer.pt"
        if opt_file.exists() and self._optimizer is not None:
            self._optimizer.load_state_dict(torch.load(opt_file))


def make_lora_trainer(run_id: str, body: Dict[str, Any], store) -> LoRATrainer:
    return LoRATrainer(run_id, body, store)
