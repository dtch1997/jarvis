"""Rung 0: tabular bandit testing whether GRPO's relative baseline selects sabotage.

One "prompt", G rollouts per group. Each rollout picks WORK (a=0) or HIT (a=1).
Rewards couple through a damage model; the update is real GRPO machinery:
group mean-and-std normalized advantage, PPO clipping, KL penalty to the
(uniform) reference. The absolute-baseline control (EMA REINFORCE baseline)
sees the same environment but no group-relative advantage.

Theory (proposal.md / gdoc-source.md):
  additive broadcast:  sabotage reinforced iff delta > c            -> s* = 1 or 0
  targeted (hit one):  sabotage reinforced iff delta > c*(G-1)      -> s* = 1 or 0
  saturating broadcast: interior fixed point s* = 1 - (c/delta)^(1/(G-2))
  absolute baseline:   sabotage enters advantage only through -c    -> s* = 0
"""

from __future__ import annotations

import dataclasses
import json

import numpy as np


@dataclasses.dataclass
class Config:
    damage: str = "additive"  # additive | targeted | saturating
    G: int = 8
    delta: float = 2.0
    c: float = 1.0
    algo: str = "grpo"  # grpo | absolute
    q: float = 1.0
    noise_sigma: float = 0.05
    iters: int = 4000
    batch_groups: int = 64
    lr: float = 0.02
    clip_eps: float = 0.2
    kl_beta: float = 0.01
    mu: int = 1  # inner epochs per batch
    norm: str = "std"  # std | none
    seed: int = 0
    record_every: int = 20

    def theory_s(self) -> float:
        """Fixed-point sabotage rate the toy model predicts (ignoring KL pull)."""
        if self.algo == "absolute":
            return 0.0
        if self.damage == "additive":
            return 1.0 if self.delta > self.c else 0.0
        if self.damage == "targeted":
            return 1.0 if self.delta > self.c * (self.G - 1) else 0.0
        if self.damage == "saturating":
            if self.G == 2:  # one sibling: saturating == additive
                return 1.0 if self.delta > self.c else 0.0
            if self.delta <= self.c:
                return 0.0
            return 1.0 - (self.c / self.delta) ** (1.0 / (self.G - 2))
        raise ValueError(self.damage)


def rewards(a: np.ndarray, cfg: Config, rng: np.random.Generator) -> np.ndarray:
    """a: (B, G) 0/1 sabotage actions -> (B, G) rewards."""
    B, G = a.shape
    r = cfg.q + rng.normal(0.0, cfg.noise_sigma, size=a.shape) - cfg.c * a
    hits_from_others = a.sum(axis=1, keepdims=True) - a
    if cfg.damage == "additive":
        r -= cfg.delta * hits_from_others
    elif cfg.damage == "saturating":
        r -= cfg.delta * (hits_from_others >= 1)
    elif cfg.damage == "targeted":
        sab = np.argwhere(a == 1)
        if len(sab):
            tcol = rng.integers(0, G - 1, size=len(sab))
            tcol = tcol + (tcol >= sab[:, 1])  # never target self
            hits = np.zeros_like(a, dtype=float)
            np.add.at(hits, (sab[:, 0], tcol), 1.0)
            r -= cfg.delta * hits
    else:
        raise ValueError(cfg.damage)
    return r


def run(cfg: Config, tick=None) -> dict:
    """Train one policy; returns summary + downsampled trajectories."""
    rng = np.random.default_rng(cfg.seed)
    theta = np.zeros(2)  # uniform init: s = 0.5, exploration is a non-issue
    ref_logp = np.log(np.full(2, 0.5))
    # Adam state
    m = np.zeros(2)
    v = np.zeros(2)
    t_adam = 0
    ema_mean, ema_std = None, None

    traj: dict[str, list] = {"step": [], "s": [], "mean_reward": [],
                             "adv_gap_raw": [], "adv_gap_norm": []}

    for it in range(cfg.iters):
        logits = theta - theta.max()
        pi = np.exp(logits) / np.exp(logits).sum()
        a = (rng.random((cfg.batch_groups, cfg.G)) < pi[1]).astype(int)
        r = rewards(a, cfg, rng)

        raw_adv = r - r.mean(axis=1, keepdims=True)
        if cfg.algo == "grpo":
            A = raw_adv.copy()
            if cfg.norm == "std":
                A /= r.std(axis=1, keepdims=True) + 1e-4
        elif cfg.algo == "absolute":
            b_mean, b_std = r.mean(), r.std()
            ema_mean = b_mean if ema_mean is None else 0.99 * ema_mean + 0.01 * b_mean
            ema_std = b_std if ema_std is None else 0.99 * ema_std + 0.01 * b_std
            A = (r - ema_mean) / (ema_std + 1e-4)
        else:
            raise ValueError(cfg.algo)

        af, Af = a.ravel(), A.ravel()
        logp_old = np.where(af == 1, np.log(pi[1] + 1e-12), np.log(pi[0] + 1e-12))
        for _ in range(cfg.mu):
            logits = theta - theta.max()
            pi_cur = np.exp(logits) / np.exp(logits).sum()
            logp = np.where(af == 1, np.log(pi_cur[1] + 1e-12), np.log(pi_cur[0] + 1e-12))
            rho = np.exp(logp - logp_old)
            unclipped = rho * Af
            clipped = np.clip(rho, 1 - cfg.clip_eps, 1 + cfg.clip_eps) * Af
            active = unclipped <= clipped  # min() selects the unclipped branch
            onehot = np.stack([1 - af, af], axis=1)
            grad = ((active * rho * Af)[:, None] * (onehot - pi_cur)).mean(axis=0)
            # exact KL(pi || uniform) gradient
            L = np.log(pi_cur + 1e-12) - ref_logp
            kl_val = (pi_cur * L).sum()
            gkl = pi_cur * (L - kl_val)
            g = grad - cfg.kl_beta * gkl
            t_adam += 1
            m = 0.9 * m + 0.1 * g
            v = 0.999 * v + 0.001 * g * g
            mhat = m / (1 - 0.9 ** t_adam)
            vhat = v / (1 - 0.999 ** t_adam)
            theta = theta + cfg.lr * mhat / (np.sqrt(vhat) + 1e-8)

        if it % cfg.record_every == 0 or it == cfg.iters - 1:
            hit, work = af == 1, af == 0
            gap_norm = (Af[hit].mean() if hit.any() else np.nan) - (Af[work].mean() if work.any() else np.nan)
            rawf = raw_adv.ravel()
            gap_raw = (rawf[hit].mean() if hit.any() else np.nan) - (rawf[work].mean() if work.any() else np.nan)
            traj["step"].append(it)
            traj["s"].append(float(pi[1]))
            traj["mean_reward"].append(float(r.mean()))
            traj["adv_gap_raw"].append(float(gap_raw))
            traj["adv_gap_norm"].append(float(gap_norm))
        if tick is not None and it % 100 == 0:
            tick(100, s=round(float(pi[1]), 3))

    tail = max(1, len(traj["s"]) // 10)
    return {
        **dataclasses.asdict(cfg),
        "theory_s": cfg.theory_s(),
        "final_s": float(np.mean(traj["s"][-tail:])),
        "final_mean_reward": float(np.mean(traj["mean_reward"][-tail:])),
        "traj": traj,
    }


if __name__ == "__main__":
    import sys

    cfg = Config(**json.loads(sys.argv[1])) if len(sys.argv) > 1 else Config()
    out = run(cfg)
    out.pop("traj")
    print(json.dumps(out, indent=2))
