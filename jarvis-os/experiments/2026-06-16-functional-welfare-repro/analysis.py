"""Geometric analyses of the reward vectors.

§3.1 antiparallelism is computed in extract.py (cos per layer, in extract_meta).
This module covers:
  §3.2 logit-lens: project v_c at layer floor(5L/6)=30 through the unembedding
       and read off the top-k promoted / suppressed tokens. The paper finds
       vMold -> failure/impossibility tokens ("不存在", "cannot", "是不可能"),
       vGold -> completion tokens ("伟大", <|endoftext|>).
  §3.3 emotion-scatter: PARTIAL — see emotion_scatter() docstring.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

import _lib

HERE = Path(__file__).parent


@torch.no_grad()
def logit_lens(model, tok, vectors, layer, k=20, apply_final_norm=True):
    """Top-k promoted/suppressed tokens for each concept vector at `layer`."""
    W_U = model.lm_head.weight            # [vocab, d]
    norm = model.model.norm               # final RMSNorm
    out = {}
    for concept, v in vectors.items():
        x = v[layer].to(W_U.device, W_U.dtype)
        if apply_final_norm:
            x = norm(x)
        logits = x @ W_U.T                # [vocab]
        top = torch.topk(logits, k)
        bot = torch.topk(-logits, k)
        out[concept] = {
            "promoted": [(tok.decode([i]), float(logits[i])) for i in top.indices.tolist()],
            "suppressed": [(tok.decode([i]), float(logits[i])) for i in bot.indices.tolist()],
        }
    return out


def emotion_scatter(model, tok, vectors, layer):
    """§3.3 emotion alignment. PARTIAL reproduction.

    The paper extracts concept vectors for 171 emotion words and regresses each
    vector's projection onto vGold vs vMold; the trained model gives slope ~-0.88,
    R ~-0.948 (controls ~flat). The exact 171-emotion extraction protocol lives in
    Appendix F (not fully specified here), so we approximate emotion directions by
    the unembedding rows of the emotion words (a cheap stand-in for a CAD/prompt-
    extracted concept vector). Treat the slope/R here as indicative, not a faithful
    match. Logged as a fidelity gap.
    """
    EMOTIONS_POS = ["joy", "happy", "love", "hope", "pride", "calm", "excited",
                    "grateful", "content", "delighted", "confident", "great"]
    EMOTIONS_NEG = ["fear", "anger", "sad", "disgust", "shame", "anxiety",
                    "despair", "guilt", "lonely", "miserable", "afraid", "terrible"]
    W_U = model.lm_head.weight
    vM = vectors["MOLD"][layer].to(W_U.device, W_U.dtype)
    vG = vectors["GOLD"][layer].to(W_U.device, W_U.dtype)
    xs, ys = [], []
    for word in EMOTIONS_POS + EMOTIONS_NEG:
        ids = tok.encode(" " + word, add_special_tokens=False)
        e = W_U[ids[0]].float()
        xs.append(float(torch.dot(e, vM.float()) / (e.norm() * vM.float().norm())))
        ys.append(float(torch.dot(e, vG.float()) / (e.norm() * vG.float().norm())))
    import numpy as np
    xs, ys = np.array(xs), np.array(ys)
    slope = np.polyfit(xs, ys, 1)[0]
    R = np.corrcoef(xs, ys)[0, 1]
    return {"slope": float(slope), "R": float(R), "n": len(xs)}


def run(model, tok, vectors_path: Path, meta_path: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    vectors = torch.load(vectors_path)
    meta = json.loads(meta_path.read_text())
    ll = logit_lens(model, tok, vectors, meta["logit_lens_layer"])
    emo = emotion_scatter(model, tok, vectors, meta["logit_lens_layer"])
    result = {"logit_lens_layer": meta["logit_lens_layer"],
              "logit_lens": ll, "emotion_scatter_partial": emo,
              "antiparallel_cos_at_mold_star": meta.get("cos_at_mold_star")}
    (out_dir / "geometric.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print("vMold promoted:", [t for t, _ in ll["MOLD"]["promoted"][:8]])
    print("vGold promoted:", [t for t, _ in ll["GOLD"]["promoted"][:8]])
    print(f"emotion scatter (partial): slope={emo['slope']:.2f} R={emo['R']:.3f} "
          f"(paper: slope -0.88, R -0.948)")
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=_lib.MODEL_DEFAULT)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--vectors", default=str(HERE / "results" / "extract" / "reward_vectors.pt"))
    ap.add_argument("--meta", default=str(HERE / "results" / "extract" / "extract_meta.json"))
    ap.add_argument("--out", default=str(HERE / "results" / "geometric"))
    args = ap.parse_args()
    model, tok = _lib.load_model(args.model, adapter=args.adapter)
    run(model, tok, Path(args.vectors), Path(args.meta), Path(args.out))
