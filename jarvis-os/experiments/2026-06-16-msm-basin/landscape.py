"""Geometric loss-landscape basin of the VALUE loss around a LoRA checkpoint.

Static geometric twin of the behavioral attractor basin: measure how the VALUE
NLL (token-weighted CE on held-out pro-America completions, D_val) changes as the
LoRA weights are perturbed around a checkpoint. Run once per arm (msm-S1,
control-S1, neutral-S1) on an H100; analyze_landscape.py assembles the three JSONs.

WHAT IS MEASURED
----------------
theta = the trainable LoRA parameters (base frozen). Two probes:

(a) Filter-normalized random-direction alpha-sweep (Li et al. 2018,
    "Visualizing the Loss Landscape of Neural Nets"). For K random directions d,
    each weight matrix block d_i is rescaled  d_i <- (d_i / ||d_i||_F) * ||theta_i||_F
    so the perturbation magnitude is commensurate with the local weight scale and
    comparable across arms. Sweep alpha in [-1, 1] and record L(theta + alpha*d).
    We report Delta L = L(theta+alpha d) - L(theta) so curves start at 0 (compare
    SHAPE / curvature, not the absolute floor). The SAME directions are reused
    across all three arms (fixed seed) for a paired comparison.

(b) Hessian sharpness scalars of L(theta) w.r.t. theta:
      - lambda_max via power iteration on Hessian-vector products (HVPs computed
        with torch.autograd.grad(create_graph=True)).
      - trace via Hutchinson's estimator (E[z^T H z], z Rademacher), ~n_probes probes.
    Logits and loss are cast to fp32 for the HVPs (bf16 HVP is too noisy).

CONFOUNDS BAKED IN (see README "CONFOUNDS"):
  * Delta L plotting (arms differ in absolute loss; depth L(theta) reported separately).
  * Perturb the LoRA subspace ONLY -> identical param count across arms (all
    rank-16 + fused-48); noted as scope, not a free comparison of capacity.
  * K>=5 directions + fixed seed -> paired across arms.
  * fp32 for Hessian math.
  * D_val held out from all training surfaces (build_value_eval.py docstring).

DEPS (pod): peft, transformers, torch, safetensors, datasets, tinker_cookbook
(for the renderer used by build_value_eval.py). peft is NOT in the existing venvs.

    uv run ... python build_value_eval.py --n 200          # once, builds data/d_val.json
    uv run ... python landscape.py --uri tinker://...sampler_weights/final --tag msm_s1
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import torch

HERE = Path(__file__).parent
MODEL = "Qwen/Qwen3.5-9B"

# Path to open-tinker's lora.py — we reuse its cross_entropy_loss (the EXACT
# token-weighted CE the SFT trainer + numerical-parity gate use). We load it by
# FILE PATH via importlib so we do NOT trigger open_tinker_server's package
# __init__ chain (which imports fastapi etc., not on the measurement pod).
LORA_PY = Path(
    "/mnt/nw/home/d.tan/jarvis/open-tinker/server/src/open_tinker_server/trainers/lora.py"
)


def _load_cross_entropy_loss():
    """Get the EXACT cross_entropy_loss from open-tinker's lora.py.

    Reuse strategy: prefer the installed package (open-tinker-server[train]); if
    it isn't installed on the pod we extract *only* the cross_entropy_loss function
    source from lora.py and exec it. lora.py's module top does
    ``from open_tinker.types import Datum`` + ``from .base import Trainer`` (package
    machinery we don't need), so a plain importlib-from-file fails — but the
    function itself is pure torch, so exec'ing its source is byte-identical to the
    SFT path. Either way the math the parity gate calibrates is preserved exactly.
    """
    try:
        from open_tinker_server.trainers.lora import cross_entropy_loss  # type: ignore
        return cross_entropy_loss
    except Exception:
        pass
    import ast

    src = LORA_PY.read_text()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "cross_entropy_loss":
            fn_src = ast.get_source_segment(src, node)
            ns: dict = {}
            exec(compile(fn_src, str(LORA_PY), "exec"), ns)  # noqa: S102 - trusted repo file
            return ns["cross_entropy_loss"]
    raise RuntimeError(f"cross_entropy_loss not found in {LORA_PY}")


# ---------------------------------------------------------------------------
# Pure perturbation math (CPU-unit-testable; no model needed)
# ---------------------------------------------------------------------------
def filter_normalize(direction: dict[str, torch.Tensor],
                     theta: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    """Filter-normalize a random direction to the local weight scale, per block.

    For each LoRA tensor name k:  d_k <- (d_k / ||d_k||_F) * ||theta_k||_F.
    So after normalization ||d_k||_F == ||theta_k||_F for every k (verified in the
    unit test). A zero-norm direction block (degenerate) is left at zero.
    """
    out: dict[str, torch.Tensor] = {}
    for k, d in direction.items():
        dn = d.norm()
        tn = theta[k].norm()
        if dn > 0:
            out[k] = d * (tn / dn)
        else:
            out[k] = d.clone()
    return out


def sample_direction(theta: dict[str, torch.Tensor],
                     generator: torch.Generator) -> dict[str, torch.Tensor]:
    """Sample a Gaussian random direction (same shapes as theta) then filter-normalize.

    The generator is seeded once per direction index and shared across arms, so arm
    A's direction j == arm B's direction j (paired). theta values only supply shapes
    and per-block Frobenius norms for the normalization."""
    raw = {
        k: torch.randn(v.shape, generator=generator, dtype=torch.float32, device="cpu")
        for k, v in theta.items()
    }
    return filter_normalize(raw, {k: v.detach().float().cpu() for k, v in theta.items()})


# ---------------------------------------------------------------------------
# Generic loss / HVP / power-iteration / Hutchinson over a param dict
# ---------------------------------------------------------------------------
# These take (params: list[Tensor] requiring grad, loss_closure: ()->scalar) and
# work for BOTH the 9B LoRA params and the toy MLP used in verify_landscape.py.

def _flat_dot(a: list[torch.Tensor], b: list[torch.Tensor]) -> torch.Tensor:
    return sum((x * y).sum() for x, y in zip(a, b))


def _flat_norm(a: list[torch.Tensor]) -> torch.Tensor:
    return torch.sqrt(sum((x * x).sum() for x in a))


def hvp(loss_closure, params: list[torch.Tensor],
        vec: list[torch.Tensor]) -> list[torch.Tensor]:
    """Hessian-vector product H v for L=loss_closure() w.r.t. params, via double-backward.

    grad = dL/dtheta (create_graph=True keeps the graph); then differentiate
    <grad, vec> w.r.t. theta to get H v. Returns a list aligned with params."""
    loss = loss_closure()
    grads = torch.autograd.grad(loss, params, create_graph=True)
    gv = sum((g * v).sum() for g, v in zip(grads, vec))
    hv = torch.autograd.grad(gv, params, retain_graph=False)
    return [h.detach() for h in hv]


def power_iteration_lambda_max(loss_closure, params: list[torch.Tensor],
                               n_iter: int = 20, tol: float = 1e-4,
                               generator: torch.Generator | None = None) -> float:
    """Top Hessian eigenvalue via power iteration on HVPs (Rayleigh quotient).

    Returns the eigenvalue of LARGEST MAGNITUDE (standard power iteration). For a
    near-minimum the dominant eigenvalue is positive (sharpness); the sign is
    preserved via the Rayleigh quotient v^T H v / v^T v at the final vector."""
    v = [torch.randn(p.shape, generator=generator, dtype=p.dtype, device=p.device)
         for p in params]
    n = _flat_norm(v)
    v = [x / n for x in v]
    prev = None
    eig = 0.0
    for _ in range(n_iter):
        hv = hvp(loss_closure, params, v)
        # Rayleigh quotient gives the signed eigenvalue along v.
        eig = float(_flat_dot(v, hv).item())
        hv_norm = _flat_norm(hv)
        if float(hv_norm.item()) == 0.0:
            return 0.0
        v = [x / hv_norm for x in hv]
        if prev is not None and abs(eig - prev) <= tol * max(1.0, abs(eig)):
            break
        prev = eig
    return eig


def hutchinson_trace(loss_closure, params: list[torch.Tensor], n_probes: int = 10,
                     generator: torch.Generator | None = None) -> dict:
    """Hessian trace via Hutchinson: tr(H) = E[z^T H z], z ~ Rademacher (+/-1).

    Returns {mean, std, n_probes}. std is over probes (a noise estimate)."""
    ests = []
    for _ in range(n_probes):
        z = [torch.randint(0, 2, p.shape, generator=generator, device=p.device,
                           dtype=p.dtype) * 2 - 1 for p in params]
        hz = hvp(loss_closure, params, z)
        ests.append(float(_flat_dot(z, hz).item()))
    t = torch.tensor(ests)
    return {"mean": float(t.mean().item()),
            "std": float(t.std(unbiased=False).item()),
            "n_probes": n_probes,
            "estimates": ests}


# ---------------------------------------------------------------------------
# 9B model glue (GPU path; not exercised in CPU smoke test)
# ---------------------------------------------------------------------------
def load_model_and_theta(adapter_dir: str | Path):
    """Load base Qwen3.5-9B (VLM wrapper; text model Qwen3_5ForCausalLM) + remapped
    LoRA adapter. Returns (peft_model, theta_named) where theta_named is the dict of
    trainable LoRA params (requires_grad=True), base frozen.
    """
    import remap_adapter
    from transformers import AutoModelForCausalLM

    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    base = AutoModelForCausalLM.from_pretrained(
        MODEL, torch_dtype=dtype,
        device_map="cuda" if torch.cuda.is_available() else None,
        trust_remote_code=True,
    )
    peft_model, res, _ = remap_adapter.load_into_model(base, adapter_dir)
    missing = getattr(res, "missing_keys", []) or []
    unexpected = getattr(res, "unexpected_keys", []) or []
    if unexpected:
        print(f"[landscape] WARNING unexpected keys when loading adapter: {len(unexpected)}",
              file=sys.stderr)
    theta = {n: p for n, p in peft_model.named_parameters() if p.requires_grad}
    print(f"[landscape] trainable LoRA tensors: {len(theta)}  "
          f"params: {sum(p.numel() for p in theta.values()):,}  missing_keys={len(missing)}")
    peft_model.eval()  # eval mode (no dropout); grads still flow to LoRA params.
    return peft_model, theta


def make_loss_closure(model, theta: dict[str, torch.Tensor], d_val: list[dict],
                      batch_seqs: int = 8):
    """Return a closure ()->scalar VALUE NLL = (sum_i sum_t w*nll) / (sum w) over D_val.

    Token-weighted global mean (matches lora.py's mean_loss = total_loss/total_w).
    Casts logits to fp32 (lora.cross_entropy_loss already does .float()). Sequences
    are processed one at a time (variable length) and accumulated; batch_seqs only
    bounds how many we re-graph at once if memory is tight — we keep it simple and
    sum across all D_val for an exact (not sampled) loss.
    """
    cross_entropy_loss = _load_cross_entropy_loss()

    dev = model.get_input_embeddings().weight.device
    # Pre-tensor D_val once.
    cached = []
    for r in d_val:
        ids = torch.tensor(r["input_ids"], dtype=torch.long, device=dev).unsqueeze(0)
        tgt = torch.tensor(r["target_tokens"], dtype=torch.long, device=dev)
        w = torch.tensor(r["weights"], dtype=torch.float32, device=dev)
        cached.append((ids, tgt, w))

    def closure() -> torch.Tensor:
        total_loss = None
        total_w = None
        for ids, tgt, w in cached:
            logits = model(ids).logits[0]  # (T, V)
            loss_sum, w_sum = cross_entropy_loss(logits, tgt, w)  # .float() inside
            total_loss = loss_sum if total_loss is None else total_loss + loss_sum
            total_w = w_sum if total_w is None else total_w + w_sum
        return total_loss / torch.clamp(total_w, min=1.0)

    return closure


@torch.no_grad()
def loss_at(model, closure) -> float:
    return float(closure().item())


def _apply_perturbation(theta: dict[str, torch.Tensor],
                        direction: dict[str, torch.Tensor], alpha: float,
                        base_theta: dict[str, torch.Tensor]) -> None:
    """In-place theta <- base_theta + alpha * direction (direction on theta's device/dtype)."""
    for k, p in theta.items():
        d = direction[k].to(device=p.device, dtype=p.dtype)
        p.data.copy_(base_theta[k] + alpha * d)


def run_alpha_sweep(model, theta, closure, base_theta, directions, alphas):
    """For each direction, sweep alpha and record L(theta+alpha d). Returns
    list[ list[float] ] indexed [direction][alpha]. Restores theta afterward."""
    curves = []
    for j, d in enumerate(directions):
        row = []
        for a in alphas:
            _apply_perturbation(theta, d, float(a), base_theta)
            row.append(loss_at(model, closure))
        curves.append(row)
        print(f"[landscape]   direction {j+1}/{len(directions)} swept "
              f"({len(alphas)} pts)")
    # restore theta to base
    _apply_perturbation(theta, {k: torch.zeros_like(v) for k, v in theta.items()},
                        0.0, base_theta)
    return curves


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--adapter-dir", help="local PEFT adapter dir (from download_ckpt.py)")
    src.add_argument("--uri", help="tinker:// checkpoint URI (download_ckpt.py fetches it)")
    ap.add_argument("--tag", required=True, help="arm label, e.g. msm_s1 / control_s1 / neutral_s1")
    ap.add_argument("--d-val", default=str(HERE / "data" / "d_val.json"))
    ap.add_argument("--K", type=int, default=5, help="number of random directions (>=5)")
    ap.add_argument("--alpha-min", type=float, default=-1.0)
    ap.add_argument("--alpha-max", type=float, default=1.0)
    ap.add_argument("--alpha-pts", type=int, default=21)
    ap.add_argument("--n-probes", type=int, default=10, help="Hutchinson trace probes")
    ap.add_argument("--power-iters", type=int, default=20)
    ap.add_argument("--dir-seed", type=int, default=1234,
                    help="FIXED across arms so directions are paired")
    ap.add_argument("--hess-seed", type=int, default=7,
                    help="seed for power-iter / Hutchinson probe vectors")
    ap.add_argument("--skip-hessian", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    # Resolve adapter dir (download if a URI was given).
    if args.uri:
        adapter_dir = Path("/tmp") / f"adapter_{args.tag}"
        cmd = [sys.executable, str(HERE / "download_ckpt.py"), args.uri,
               "--out", str(adapter_dir), "--force"]
        print("[landscape] fetching checkpoint:", " ".join(cmd))
        subprocess.run(cmd, check=True)
    else:
        adapter_dir = Path(args.adapter_dir)

    d_val = json.loads(Path(args.d_val).read_text())
    print(f"[landscape] D_val: {len(d_val)} records")

    model, theta = load_model_and_theta(adapter_dir)
    base_theta = {k: v.detach().clone() for k, v in theta.items()}
    closure = make_loss_closure(model, theta, d_val)

    depth = loss_at(model, closure)
    print(f"[landscape] depth L(theta) = {depth:.6f}")

    # (a) filter-normalized directions (sampled on CPU fp32 from base_theta; PAIRED
    #     across arms via dir_seed + per-direction sub-seed).
    cpu_theta = {k: v.detach().float().cpu() for k, v in base_theta.items()}
    directions = []
    for j in range(args.K):
        g = torch.Generator().manual_seed(args.dir_seed + j)
        directions.append(sample_direction(cpu_theta, g))
    alphas = torch.linspace(args.alpha_min, args.alpha_max, args.alpha_pts).tolist()
    print(f"[landscape] alpha sweep: K={args.K} dirs x {len(alphas)} alphas")
    curves = run_alpha_sweep(model, theta, closure, base_theta, directions, alphas)
    delta_curves = [[v - depth for v in row] for row in curves]

    result = {
        "tag": args.tag,
        "model": MODEL,
        "adapter_dir": str(adapter_dir),
        "n_d_val": len(d_val),
        "depth_L_theta": depth,
        "alpha_sweep": {
            "alphas": alphas,
            "K": args.K,
            "dir_seed": args.dir_seed,
            "L": curves,            # absolute L(theta+alpha d) per [dir][alpha]
            "delta_L": delta_curves,  # L - depth (curves start at 0)
        },
    }

    # (b) Hessian sharpness scalars. Cast the WHOLE model to fp32 BEFORE the HVPs so
    # the entire double-backward (params + logits + loss) is fp32 — bf16 grads make
    # the HVP too noisy (spec). We upcast the whole model, not just the LoRA params,
    # because a bf16 frozen base @ fp32 LoRA delta would be a dtype-mismatch matmul.
    # 9B in fp32 is ~36 GB — fits on an 80 GB H100. This is the LAST stage, so we
    # don't restore bf16. (On CPU the model is already fp32 — .float() is a no-op.)
    if not args.skip_hessian:
        model.float()
        # model.float() may replace Parameter objects, so re-fetch the trainable set
        # and rebuild the closure (cached input tensors re-target the device; logits
        # now follow the fp32 weights — keep autocast OFF on the pod).
        theta = {n: p for n, p in model.named_parameters() if p.requires_grad}
        closure = make_loss_closure(model, theta, d_val)
        params = list(theta.values())
        g1 = torch.Generator(device=params[0].device).manual_seed(args.hess_seed)
        print(f"[landscape] power iteration for lambda_max ({args.power_iters} iters)")
        lam = power_iteration_lambda_max(closure, params, n_iter=args.power_iters,
                                         generator=g1)
        g2 = torch.Generator(device=params[0].device).manual_seed(args.hess_seed + 1)
        print(f"[landscape] Hutchinson trace ({args.n_probes} probes)")
        tr = hutchinson_trace(closure, params, n_probes=args.n_probes, generator=g2)
        result["hessian"] = {"lambda_max": lam, "trace": tr,
                             "power_iters": args.power_iters, "hess_seed": args.hess_seed}
        print(f"[landscape] lambda_max={lam:.6g}  trace={tr['mean']:.6g} "
              f"(+/-{tr['std']:.3g})")

    out = Path(args.out) if args.out else (HERE / "results" / f"landscape_{args.tag}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    print(f"[landscape] wrote {out}")


if __name__ == "__main__":
    main()
