"""Dump real eNTK training trajectories to entk_data.js for the HTML widgets.

For the lazy (wide) and rich (narrow) nets, record at log-spaced checkpoints:
step, kernel drift, kernel-target alignment (CKA), and the top eNTK eigenvalues.
The §3 scrubber widget reads window.ENTK from this file.
"""
import json
import numpy as np
import torch

import blog_figures as bf  # functions only; figures run under __main__ guard


def run(width, steps=4000, n_ckpt=24, n_eig=40):
    X, y = bf.make_data()
    model = bf.MLP(width)
    K0 = bf.entk(model, X)
    lr = 0.2 / torch.linalg.eigvalsh(K0).max().item()
    Kyy = torch.outer(y, y)
    ckpts = sorted(set(np.unique(np.r_[0, np.geomspace(1, steps, n_ckpt)]).astype(int)))
    opt = torch.optim.SGD(model.parameters(), lr=lr)
    out = []
    for s in range(steps + 1):
        r = model(X) - y
        if s in ckpts:
            K = bf.entk(model, X)
            ev = torch.linalg.eigvalsh(K).flip(0)[:n_eig].clamp_min(1e-12)
            out.append(dict(step=int(s),
                            drift=round(((K - K0).norm() / K0.norm()).item(), 4),
                            cka=round(bf.cka(K, Kyy), 4),
                            spectrum=[round(v, 6) for v in ev.tolist()]))
        opt.zero_grad()
        (0.5 * (r ** 2).sum()).backward()
        opt.step()
    return dict(lr=round(lr, 5), n_eig=n_eig, ckpts=out)


data = {"lazy": run(4096), "rich": run(32)}
with open("/mnt/nw/home/d.tan/jarvis/experiments/2026-06-16-entk-toy/entk_data.js", "w") as f:
    f.write("window.ENTK = " + json.dumps(data, separators=(",", ":")) + ";\n")
print("lazy lr", data["lazy"]["lr"], "rich lr", data["rich"]["lr"],
      "| checkpoints", len(data["lazy"]["ckpts"]))
print("rich top-eig: init", data["rich"]["ckpts"][0]["spectrum"][0],
      "-> final", data["rich"]["ckpts"][-1]["spectrum"][0])
print("saved entk_data.js")
