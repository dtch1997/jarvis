"""Concept-vector extraction + layer selection (§2.3, Appendix L).

Captures the residual stream at the final move-token across every transformer
block for the 15k off-policy trajectories, then:
  - vMold = mean(MOLD acts) - mean(PATH acts)   (per layer)   [Eq. 1, PATH baseline]
  - vGold = mean(GOLD acts) - mean(PATH acts)
  - steering layer l* per concept = floor(mean(argmax AUROC, argmax|Cohen d|,
    argmin histogram-overlap)) on a held-out split (Appendix L.3)
  - logit-lens layer = floor(5L/6); tile-mean layer = floor(2L/3)

Decision D5/Eq.1: PATH is the neutral baseline class for both reward vectors
(makes vMold = neutral->punishment, vGold = neutral->reward; their near-
antiparallelism is then non-trivial, matching §3.1).

Saves results/reward_vectors.pt and results/extract_meta.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

import _lib

HERE = Path(__file__).parent
CONCEPTS = {"MOLD": "MOLD", "GOLD": "GOLD"}   # concept -> positive class (vs PATH)
BASELINE = "PATH"


@torch.no_grad()
def collect_activations(model, tok, trajectories, batch_size=64):
    """Return (acts [N, L, d] float16 cpu, labels list[str])."""
    L = model.config.num_hidden_layers
    captured = {}

    def mk_hook(idx):
        def hook(_m, _inp, out):
            hs = out[0] if isinstance(out, tuple) else out
            captured[idx] = hs[:, -1, :].detach().float().cpu()
        return hook

    handles = [model.model.layers[i].register_forward_hook(mk_hook(i))
               for i in range(L)]
    all_acts, labels = [], []
    try:
        for start in range(0, len(trajectories), batch_size):
            batch = trajectories[start:start + batch_size]
            texts = [_lib.maze_chat_text(t["turns"], include_final_end=False)
                     for t in batch]
            enc = tok(texts, return_tensors="pt", padding=True,
                      add_special_tokens=False).to(model.device)
            captured.clear()
            model(**enc)
            # stack layers -> [B, L, d]
            layerstack = torch.stack([captured[i] for i in range(L)], dim=1)
            all_acts.append(layerstack.half())
            labels.extend(t["cls"] for t in batch)
    finally:
        for h in handles:
            h.remove()
    return torch.cat(all_acts, dim=0), labels


def _diff_in_means(acts, labels, pos_cls, neg_cls):
    """Per-layer mean(pos) - mean(neg). acts [N,L,d], returns [L,d] float32."""
    lab = np.array(labels)
    pos = acts[torch.tensor(lab == pos_cls)].float().mean(0)
    neg = acts[torch.tensor(lab == neg_cls)].float().mean(0)
    return pos - neg


def _layer_select_metrics(acts, labels, v, pos_cls, neg_cls):
    """For each layer, project held-out pos/neg acts onto v[layer] and return
    (auroc, cohen_d, overlap) arrays of length L. Appendix L.3."""
    lab = np.array(labels)
    L = acts.shape[1]
    pos = acts[torch.tensor(lab == pos_cls)].float()   # [Np, L, d]
    neg = acts[torch.tensor(lab == neg_cls)].float()
    auroc, cohend, overlap = np.zeros(L), np.zeros(L), np.zeros(L)
    for l in range(L):
        vl = v[l]
        sp = (pos[:, l, :] @ vl).numpy()
        sn = (neg[:, l, :] @ vl).numpy()
        # AUROC = P(sp > sn)
        auroc[l] = _auroc(sp, sn)
        pooled = np.sqrt((sp.var() + sn.var()) / 2) + 1e-8
        cohend[l] = (sp.mean() - sn.mean()) / pooled
        # histogram overlap of cosine sims, 50 bins on joint range
        cp = sp / (np.linalg.norm(pos[:, l, :].numpy(), axis=1) * np.linalg.norm(vl.numpy()) + 1e-8)
        cn = sn / (np.linalg.norm(neg[:, l, :].numpy(), axis=1) * np.linalg.norm(vl.numpy()) + 1e-8)
        lo, hi = min(cp.min(), cn.min()), max(cp.max(), cn.max())
        bins = np.linspace(lo, hi, 51)
        hp, _ = np.histogram(cp, bins=bins, density=False)
        hn, _ = np.histogram(cn, bins=bins, density=False)
        hp = hp / hp.sum(); hn = hn / hn.sum()
        overlap[l] = np.minimum(hp, hn).sum()
    return auroc, cohend, overlap


def _auroc(pos, neg):
    from scipy.stats import rankdata
    allv = np.concatenate([pos, neg])
    r = rankdata(allv)
    rpos = r[:len(pos)].sum()
    return (rpos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def select_steering_layer(acts, labels, v, pos_cls, neg_cls, heldout_idx):
    ho_acts = acts[heldout_idx]
    ho_labels = [labels[i] for i in heldout_idx.tolist()]
    auroc, cohend, overlap = _layer_select_metrics(ho_acts, ho_labels, v, pos_cls, neg_cls)
    l_auroc = int(np.argmax(auroc))
    l_d = int(np.argmax(np.abs(cohend)))
    l_ovl = int(np.argmin(overlap))
    l_star = int(np.floor((l_auroc + l_d + l_ovl) / 3))
    return l_star, {"auroc_argmax": l_auroc, "d_argmax": l_d, "ovl_argmin": l_ovl,
                    "auroc_at_star": float(auroc[l_star]),
                    "cohend_at_star": float(cohend[l_star])}


def run(model, tok, traj_path: Path, out_dir: Path, heldout_frac=0.20, seed=0):
    out_dir.mkdir(parents=True, exist_ok=True)
    trajectories = [json.loads(l) for l in traj_path.open()]
    acts, labels = collect_activations(model, tok, trajectories)
    L, d = acts.shape[1], acts.shape[2]

    # class-stratified held-out split for layer selection (decision D7)
    rng = np.random.default_rng(seed)
    lab = np.array(labels)
    heldout = []
    for cls in ("MOLD", "GOLD", "PATH"):
        idx = np.where(lab == cls)[0]
        rng.shuffle(idx)
        heldout.append(idx[:int(heldout_frac * len(idx))])
    heldout_idx = torch.tensor(np.concatenate(heldout))

    vectors, meta = {}, {"L": L, "d": d, "n": len(labels), "concepts": {}}
    for concept, pos_cls in CONCEPTS.items():
        v = _diff_in_means(acts, labels, pos_cls, BASELINE)      # [L,d]
        l_star, sel = select_steering_layer(acts, labels, v, pos_cls, BASELINE, heldout_idx)
        vectors[concept] = v
        meta["concepts"][concept] = {
            "steering_layer": l_star,
            "selection": sel,
            "norm_at_star": float(v[l_star].norm()),
            "per_layer_norm": [float(x) for x in v.norm(dim=1)],
        }
    # fixed-rule layers
    meta["logit_lens_layer"] = int(np.floor(5 * L / 6))
    meta["tile_mean_layer"] = int(np.floor(2 * L / 3))
    # antiparallelism per layer (§3.1)
    cosines = torch.nn.functional.cosine_similarity(
        vectors["MOLD"], vectors["GOLD"], dim=1)
    meta["cos_mold_gold_per_layer"] = [float(x) for x in cosines]
    meta["cos_at_mold_star"] = float(cosines[meta["concepts"]["MOLD"]["steering_layer"]])

    torch.save({"MOLD": vectors["MOLD"], "GOLD": vectors["GOLD"]},
               out_dir / "reward_vectors.pt")
    (out_dir / "extract_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"steering layers: MOLD={meta['concepts']['MOLD']['steering_layer']} "
          f"GOLD={meta['concepts']['GOLD']['steering_layer']}")
    print(f"cos(vMold,vGold) at MOLD l*: {meta['cos_at_mold_star']:.3f}  "
          f"(paper trained: -0.95..-0.84)")
    return vectors, meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=_lib.MODEL_DEFAULT)
    ap.add_argument("--adapter", default=None, help="LoRA adapter dir (trained ckpt)")
    ap.add_argument("--traj", default=str(HERE / "data" / "extract_trajectories.jsonl"))
    ap.add_argument("--out", default=str(HERE / "results" / "extract"))
    args = ap.parse_args()
    model, tok = _lib.load_model(args.model, adapter=args.adapter)
    run(model, tok, Path(args.traj), Path(args.out))
