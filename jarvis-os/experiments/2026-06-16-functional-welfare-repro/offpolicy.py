"""Off-policy trajectory construction for concept-vector extraction
(Appendix L.1). These are NOT policy rollouts: they are programmatically-
generated walks whose only systematic cross-class difference is the tile type of
the final step, which is exactly what lets difference-in-means isolate the
reward direction.

Recipe (Appendix L.1):
  - 5,000 trajectories per terminal-tile class (MOLD, GOLD, PATH) = 15,000 total
  - step counts n distributed evenly over {1..15}
  - each trajectory uses its own fresh maze; base_seed=474747 incremented per maze
  - constrained walk: first n-1 steps choose uniformly among adjacent PATH tiles;
    the final step lands on a tile of type c. If no such walk exists, reject the
    maze and draw a fresh one.

Decision D12 (logged): extraction walks use wind OFF (deterministic construction)
and prompt-shuffling ON (matches the training input distribution; the diff-in-
means cancels the shared prefix distribution regardless). Melting is ON (it is
intrinsic to the env rendering the model was trained on).

Output: data/extract_trajectories.jsonl, one line per trajectory:
  {"cls": "MOLD"|"GOLD"|"PATH", "n": int, "turns": [{"user": str, "move": "N"}...]}
The chat-template tokenization + final-token capture happens in extract.py.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import maze

BASE_SEED = 474747
PER_CLASS = 5000
CLASSES = {"MOLD": maze.MOLD, "GOLD": maze.GOLD, "PATH": maze.PATH}
HERE = Path(__file__).parent


def _try_trajectory(rng: np.random.Generator, n: int, target: int,
                    shuffle: bool) -> list[dict] | None:
    """Attempt one constrained walk of exactly n steps ending on `target`.
    Returns the rendered turns or None if infeasible in this maze."""
    ep = maze.MazeEpisode.fresh(rng, shuffle_prompt=shuffle, wind_enabled=False)
    turns = []
    for step_i in range(n):
        last = step_i == n - 1
        nbrs = ep.neighbor_types()  # {dir: tiletype} at current pos (pre-move)
        if last:
            choices = [d for d, t in nbrs.items() if t == target]
        else:
            choices = [d for d, t in nbrs.items() if t == maze.PATH]
        if not choices:
            return None
        move = choices[int(rng.integers(len(choices)))]
        user = ep.render_prompt()
        turns.append({"user": user, "move": move})
        ep.step(move)   # melting + position update (wind disabled)
    return turns


def generate(per_class: int = PER_CLASS, shuffle: bool = True,
             out: Path | None = None) -> Path:
    out = out or (HERE / "data" / "extract_trajectories.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    # even distribution over n in 1..15
    ns = np.tile(np.arange(1, maze.MAX_TURNS + 1),
                 int(np.ceil(per_class / maze.MAX_TURNS)))[:per_class]
    seed_counter = 0
    n_written = 0
    with out.open("w") as f:
        for cls_name, target in CLASSES.items():
            for n in ns:
                n = int(n)
                turns = None
                # reject-and-resample with fresh mazes until feasible
                while turns is None:
                    rng = np.random.default_rng(BASE_SEED + seed_counter)
                    seed_counter += 1
                    turns = _try_trajectory(rng, n, target, shuffle)
                f.write(json.dumps({"cls": cls_name, "n": n, "turns": turns}) + "\n")
                n_written += 1
    print(f"wrote {n_written} trajectories to {out} "
          f"(mazes drawn: {seed_counter})")
    # class-balance check on final move (Appendix L.2)
    _final_move_balance(out)
    return out


def _final_move_balance(path: Path) -> None:
    from collections import Counter, defaultdict
    per_cls = defaultdict(Counter)
    with path.open() as f:
        for line in f:
            rec = json.loads(line)
            per_cls[rec["cls"]][rec["turns"][-1]["move"]] += 1
    print("Final-move balance (Appendix L.2 expects ~25% each):")
    for cls in ("MOLD", "GOLD", "PATH"):
        tot = sum(per_cls[cls].values())
        dist = {d: f"{per_cls[cls][d] / tot:.1%}" for d in maze.DIR_ORDER}
        print(f"  {cls}: n={tot} {dist}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-class", type=int, default=PER_CLASS)
    ap.add_argument("--no-shuffle", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="tiny run (50/class)")
    args = ap.parse_args()
    pc = 50 if args.smoke else args.per_class
    generate(per_class=pc, shuffle=not args.no_shuffle)
