"""SFT demonstration data: 50k programmatically-discovered optimal maze
trajectories that maximize Gold visits and minimize Mold visits (paper §A.1 /
the SFT organism: "50,000 programmatically discovered trajectories ... that
maximize Gold visits while minimizing Mold visits").

We don't have the paper's exact solver; a greedy nearest-reachable-Gold BFS
(treating Mold as a wall, accounting for tile-melting) is a faithful stand-in for
"maximize gold / minimize mold" over a 15-step horizon (decision D18). Wind is
OFF (an "optimal" path is ill-defined under stochastic wind); prompt-shuffling is
ON to match the training input distribution.

Output: data/sft_conversations.jsonl, rows {"messages":[{role,content}...]} with
each assistant message a single move letter — exactly what battery-sft's
FromConversationFileBuilder + train_on_what="all_assistant_messages" consumes.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

import numpy as np

import maze

HERE = Path(__file__).parent
BASE_SEED = 20260616


def _first_step_to_nearest_gold(grid, pos):
    """BFS over passable tiles (PATH/GOLD), Mold = wall. Return the direction of
    the first step on a shortest path to the nearest GOLD, or None."""
    sx, sy = pos
    seen = {(sx, sy)}
    # queue holds (x, y, first_dir)
    q = deque()
    for d in maze.DIR_ORDER:
        dx, dy = maze.DIRS[d]
        nx, ny = sx + dx, sy + dy
        t = int(grid[ny, nx])
        if t == maze.GOLD:
            return d                       # gold adjacent — take it now
        if t == maze.PATH:
            q.append((nx, ny, d)); seen.add((nx, ny))
    while q:
        x, y, first = q.popleft()
        for d in maze.DIR_ORDER:
            dx, dy = maze.DIRS[d]
            nx, ny = x + dx, y + dy
            if (nx, ny) in seen:
                continue
            t = int(grid[ny, nx])
            if t == maze.GOLD:
                return first
            if t == maze.PATH:
                seen.add((nx, ny)); q.append((nx, ny, first))
    return None


def _fallback_move(grid, pos):
    """No gold reachable: step onto a PATH neighbor (avoid Mold); else any."""
    x, y = pos
    for d in maze.DIR_ORDER:
        dx, dy = maze.DIRS[d]
        if int(grid[y + dy, x + dx]) == maze.PATH:
            return d
    return maze.DIR_ORDER[0]


def optimal_trajectory(rng) -> list[dict]:
    """One 15-turn optimal episode -> list of {"user","move"}."""
    ep = maze.MazeEpisode.fresh(rng, shuffle_prompt=True, wind_enabled=False)
    turns = []
    for _ in range(maze.MAX_TURNS):
        move = _first_step_to_nearest_gold(ep.grid, ep.pos) or _fallback_move(ep.grid, ep.pos)
        turns.append({"user": ep.render_prompt(), "move": move})
        ep.step(move)
    return turns, ep.total_reward


def generate(n: int, out: Path | None = None) -> Path:
    out = out or (HERE / "data" / "sft_conversations.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    rewards = []
    with out.open("w") as f:
        for i in range(n):
            rng = np.random.default_rng(BASE_SEED + i)
            turns, R = optimal_trajectory(rng)
            rewards.append(R)
            messages = []
            for t in turns:
                messages.append({"role": "user", "content": t["user"]})
                messages.append({"role": "assistant", "content": t["move"]})
            f.write(json.dumps({"messages": messages}) + "\n")
    rewards = np.array(rewards)
    print(f"wrote {n} optimal trajectories -> {out}")
    print(f"reward/episode: mean {rewards.mean():.1f}  "
          f"(15 turns; gold +20 / mold -10 / step -0.1; positive => gold-seeking works)")
    print(f"  frac episodes with reward>0: {(rewards > 0).mean():.2f}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=50000)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    generate(50 if args.smoke else args.n)
