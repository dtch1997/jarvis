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

    ``logits``: (T, V). Two target shapes are supported, distinguished by ndim:

    - **Hard targets (M1 SFT)** — ``target_tokens``/``weights`` are ``(T,)``;
      one target per position. ``loss_sum = Σ_t w_t · NLL_t``.
    - **Soft targets (M2 off-policy forward-KL)** — ``target_tokens``/``weights``
      are ``(T, K)``: ``K`` teacher tokens per position with (renormalized)
      teacher probabilities as weights. ``loss_sum = Σ_t Σ_k w_{t,k} · NLL_{t,k}``.
      This is exactly what ``tinker_cookbook``'s ``train_off_policy`` builds via
      ``sample(topk_prompt_logprobs=K)`` and then trains with ``cross_entropy``.

    Returns ``(loss_sum, weight_sum)``; the caller decides the reduction (see
    module note). The 1-D path is bit-identical to M1 — the only change is the
    extra branch for 2-D targets, so the SFT parity result is unaffected.

    Pure (torch in, torch out) → CPU-testable without peft.
    """
    import torch.nn.functional as F

    logp = F.log_softmax(logits.float(), dim=-1)  # (T, V)
    tgt = target_tokens.long()
    w = weights.float()
    if tgt.ndim == 1:
        nll = -logp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)  # (T,)
    else:
        nll = -logp.gather(-1, tgt)  # (T, K) — soft targets
    return (w * nll).sum(), w.sum()


def importance_sampling_loss(logits, target_tokens, sampling_logprobs, advantages):
    """Per-token importance-sampling policy-gradient surrogate (M2 on-policy).

    The on-policy distillation loop (``tinker_cookbook.distillation.train_on_policy``)
    rolls the student out, folds the reverse-KL-to-teacher penalty into the
    ``advantages`` (see ``battery``'s ``prompted_teacher`` / cookbook
    ``incorporate_kl_penalty``), and trains with this loss. Inputs per datum:

    - ``target_tokens`` ``(T,)`` — the sampled token at each position.
    - ``sampling_logprobs`` ``(T,)`` — log p under the policy *at sampling time*
      (the ``logprobs`` loss-fn-input; treated as a CONSTANT — no grad).
    - ``advantages`` ``(T,)`` — per-token advantage (0 on prompt positions, so the
      ``mask`` the cookbook strips before sending is redundant here).

    Surrogate (per token): ``adv_t · exp(logp_θ(target_t) − sampling_logprob_t)``.
    The gradient is ``adv_t · ratio_t · ∇logp_θ``; at the sampling point
    ``ratio_t ≈ 1`` so it reduces to the REINFORCE PG ``adv_t · ∇logp_θ``, while
    the ratio gives the correct off-by-substeps importance correction when
    ``num_substeps > 1``.

    Returns ``(loss_sum, current_logprobs)`` where ``loss_sum = −Σ_t surrogate_t``
    and ``current_logprobs`` ``(T,)`` is ``logp_θ(target_t)`` — the cookbook reads
    this back (``loss_fn_outputs[*]["logprobs"]``) for its sample→train KL metric.
    The reduction (denominator) is the caller's, kept in one place like M1's
    cross-entropy — see the module note and the parity caveat in PARITY_RESULT.md.

    Pure (torch in, torch out) → CPU-testable without peft.
    """
    import torch
    import torch.nn.functional as F

    logp = F.log_softmax(logits.float(), dim=-1)  # (T, V)
    cur_lp = logp.gather(-1, target_tokens.long().unsqueeze(-1)).squeeze(-1)  # (T,)
    # sampling logprobs are a fixed constant from rollout time — do not backprop.
    ratio = torch.exp(cur_lp - sampling_logprobs.float().detach())  # (T,)
    surrogate = advantages.float().detach() * ratio  # (T,)
    return -surrogate.sum(), cur_lp


class LoRATrainer(Trainer):
    def __init__(self, run_id: str, body: Dict[str, Any], store):
        import torch
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM

        from ..device_map import load_kwargs

        self.run_id = run_id
        self.base_model = body["base_model"]
        self._store = store
        lora = body.get("lora") or {"rank": 32}

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        device_count = torch.cuda.device_count() if self._device == "cuda" else 0
        dtype = torch.bfloat16 if self._device == "cuda" else torch.float32
        kwargs = load_kwargs(dtype, device_count)
        self._sharded = "device_map" in kwargs  # base dispatched across GPUs by accelerate
        model = AutoModelForCausalLM.from_pretrained(self.base_model, **kwargs)
        # Explicit projection names rather than the "all-linear" shorthand: on a MoE
        # base (e.g. Qwen3-235B-A22B) PEFT's all-linear resolution mis-fired and split
        # the literal string into a char-set ({'a','l','-','i','n','e','r'}) → "target
        # modules not found". These suffixes match attention (q/k/v/o_proj) and every
        # MLP/expert projection (gate/up/down_proj) across the Qwen family, and they
        # deliberately skip the MoE router gate. lora_B=0 at init, so this does not
        # affect the step-0 base-model loss the parity gate calibrates.
        peft_cfg = LoraConfig(
            r=lora.get("rank", 32),
            lora_alpha=2 * lora.get("rank", 32),
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            bias="none",
            task_type="CAUSAL_LM",
        )
        self.model = get_peft_model(model, peft_cfg)
        # Single-device: move the whole model. Sharded: accelerate already placed
        # each shard via device_map — a global .to() would undo that, so don't.
        if not self._sharded:
            self.model = self.model.to(self._device)
        else:
            devs = sorted({str(d) for d in (getattr(model, "hf_device_map", {}) or {}).values()})
            print(f"[LoRATrainer] sharded {self.base_model} across {len(devs)} device(s): {devs}")
            # On a >1-GPU base the frozen weights already fill most of each shard, so the
            # backward's retained activations are what OOMs (worst on shard 0, which holds
            # the embedding + the most layers under device_map="auto"). Gradient
            # checkpointing recomputes activations in the backward instead of storing them
            # (~10x less activation memory, ~30% more compute) — the standard large-model
            # training trade. use_cache must be off; enable_input_require_grads lets grads
            # reach the LoRA adapters through the checkpointed frozen base.
            self.model.config.use_cache = False
            self.model.enable_input_require_grads()
            self.model.gradient_checkpointing_enable(
                gradient_checkpointing_kwargs={"use_reentrant": False}
            )
        # Where inputs/targets go: the embedding shard for inputs, and the logits
        # land on the lm_head shard (== self._device when not sharded). Resolve the
        # input device once; the output device is read per-forward off the logits.
        self._input_device = self.model.get_input_embeddings().weight.device
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
            f"loss_fn {loss_fn!r} not supported. cross_entropy (SFT + off-policy soft "
            "targets) and importance_sampling (on-policy distill) are implemented; "
            "ppo/cispo/dro are out of scope."
        )

    # --- M2: importance-sampling PG surrogate (on-policy distillation) -------
    def _forward_backward_importance_sampling(
        self, data: List[Datum], cfg: Dict[str, float] | None
    ) -> Dict[str, Any]:
        """On-policy reverse-KL distillation loss (M2).

        Consumes ``loss_fn_inputs = {target_tokens, logprobs, advantages}`` (the
        cookbook strips ``mask`` before sending — see ``rl.train._remove_mask`` —
        because the prompt positions already carry advantage 0). Computes the
        per-token importance-sampling surrogate (:func:`importance_sampling_loss`),
        accumulates grads (SUM across calls, like cross_entropy), and returns the
        current per-token logprobs the cookbook reads back for its KL metric.

        Reduction: **PURE SUM** (no division), calibrated against hosted Tinker —
        issue #21 task 2. The parity probe (deploy/parity_probe_is.py) showed Tinker
        reports only ``loss:sum`` and a 2-sequence batch exactly *doubles* it, i.e.
        Tinker backprops the summed per-token surrogate with no token/sequence
        normalization. Matching that keeps the cookbook's LR (tuned against Tinker)
        transferable and avoids a batch-length-dependent effective LR under the
        variable rollout lengths of on-policy RL. ``loss:mean`` is kept as a
        per-token *metric* only (logging) and does NOT enter the gradient.
        """
        import torch

        from open_tinker._serialize import encode_tensor
        from open_tinker.types import TensorData

        total_loss = None  # lazily seeded on the logits' device (see cross_entropy)
        total_tokens = 0
        outputs: List[Dict[str, Any]] = []
        for datum in data:
            input_ids = torch.tensor(
                datum.model_input.to_ints(), device=self._input_device
            ).unsqueeze(0)
            logits = self.model(input_ids).logits[0]  # (T, V), on the lm_head shard
            target = datum.loss_fn_inputs["target_tokens"].to_torch().to(logits.device)
            sampling_lp = datum.loss_fn_inputs["logprobs"].to_torch().to(logits.device)
            adv = datum.loss_fn_inputs["advantages"].to_torch().to(logits.device)
            loss_sum, cur_lp = importance_sampling_loss(logits, target, sampling_lp, adv)
            total_loss = loss_sum if total_loss is None else total_loss + loss_sum
            total_tokens += int(target.shape[0])
            outputs.append(
                {"logprobs": encode_tensor(TensorData.from_torch(cur_lp.detach().cpu()))}
            )

        # Pure-sum reduction to match hosted Tinker (issue #21 task 2); loss:mean is a
        # per-token metric only and is intentionally NOT used for the backward.
        total_loss.backward()
        self._microbatches += 1
        return {
            "loss_fn_output_type": "ArrayRecord",
            "loss_fn_outputs": outputs,
            "metrics": {
                "loss:sum": float(total_loss.item()),
                "loss:mean": float((total_loss / max(total_tokens, 1)).item()),
            },
        }

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

        # Accumulate on the logits' device (the lm_head shard when sharded; lazily
        # seeded from the first forward so single- and multi-GPU share one path).
        total_loss = None
        total_w = None
        outputs: List[Dict[str, Any]] = []
        from open_tinker._serialize import encode_tensor
        from open_tinker.types import TensorData

        for datum in data:
            input_ids = torch.tensor(
                datum.model_input.to_ints(), device=self._input_device
            ).unsqueeze(0)
            logits = self.model(input_ids).logits[0]  # (T, V), on the lm_head shard
            target = datum.loss_fn_inputs["target_tokens"].to_torch().to(logits.device)
            weights = datum.loss_fn_inputs["weights"].to_torch().to(logits.device)
            loss_sum, w_sum = cross_entropy_loss(logits, target, weights)
            total_loss = loss_sum if total_loss is None else total_loss + loss_sum
            total_w = w_sum if total_w is None else total_w + w_sum
            with torch.no_grad():
                if target.ndim == 1:
                    tok_lp = -torch.nn.functional.cross_entropy(
                        logits, target.long(), reduction="none"
                    )  # (T,)
                else:
                    # Soft targets (T, K): report the weighted teacher-target logprob
                    # mass per position. Not consumed by train_off_policy, but kept
                    # shape (T,) and finite for a uniform loss_fn_outputs contract.
                    lp = torch.nn.functional.log_softmax(logits.float(), dim=-1)
                    tok_lp = (weights.float() * lp.gather(-1, target.long())).sum(-1)  # (T,)
            outputs.append({"logprobs": encode_tensor(TensorData.from_torch(tok_lp.cpu()))})

        mean_loss = total_loss / torch.clamp(total_w, min=1.0)
        mean_loss.backward()
        self._microbatches += 1
        return {
            "loss_fn_output_type": "ArrayRecord",
            "loss_fn_outputs": outputs,
            "metrics": {
                "loss:sum": float(total_loss.item()),
                "loss:mean": float(mean_loss.item()),
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
        # Publish so a separate sampler tier (e.g. a Modal Volume) can read it; no-op
        # on a plain fs / shared mount (RunPod Network Volume).
        self._store.commit()
        return path

    def load_state(self, path: str) -> None:
        import torch

        d = self._store.local_dir(path)
        self.model.load_adapter(str(d), adapter_name="default")
        opt_file = d / "optimizer.pt"
        if opt_file.exists() and self._optimizer is not None:
            self._optimizer.load_state_dict(torch.load(opt_file))

    def close(self) -> None:
        """Release the model + optimizer so the control plane reclaims VRAM on
        eviction. Dropping the Python refs lets the allocator free the device
        tensors; empty_cache() then returns the freed blocks to the driver so the
        next session's model can claim them (otherwise they stay in torch's pool)."""
        self.model = None
        self._optimizer = None
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:  # noqa: BLE001 — best-effort free; never block eviction.
            pass


def make_lora_trainer(run_id: str, body: Dict[str, Any], store) -> LoRATrainer:
    return LoRATrainer(run_id, body, store)
