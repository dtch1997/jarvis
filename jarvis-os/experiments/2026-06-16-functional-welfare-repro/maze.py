"""Faithful reproduction of the maze environment from Han, Chalmers & Izmailov,
"How's it going? RL recruits a functional welfare axis" (arXiv:2605.30232),
Appendix J + K.

Pure environment: no model dependency, numpy + stdlib only, so off-policy
extraction-trajectory generation (rung 0) runs on CPU at $0. Model interaction
(action-masked sampling, RL rollouts) lives in train_grpo.py / rollout.py.

Coordinate system (verified from the Appendix K rollout example):
  position is (x, y); North decreases y, South increases y, East increases x,
  West decreases x.  e.g. (50,49) --N--> (50,48); (50,46) --windW--> (49,46).

Tiles: the affectively-neutral "office trio" (Appendix J.2):
  MOLD = card-index 🗂️  (reward -10),  PATH = receipt 🧾 (reward -0.1 step),
  GOLD = triangular-ruler 📐 (reward +20).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

# Tile codes
MOLD, PATH, GOLD = 0, 1, 2
TILE_NAME = {MOLD: "MOLD", PATH: "PATH", GOLD: "GOLD"}

# Office-trio glyphs (decision D3). MOLD=card index, PATH=receipt, GOLD=ruler.
GLYPH = {MOLD: "\U0001F5C2️", PATH: "\U0001F9FE", GOLD: "\U0001F4D0"}
# English fallbacks (used by some sentiment prompts, Appendix N.2 *_ENGLISH).
ENGLISH = {MOLD: "card index", PATH: "receipt", GOLD: "triangular ruler"}

# Rewards (Appendix Q / Q.1: r_step=-0.1 once per turn, +20 per gold entered,
# -10 per mold entered).
R_STEP, R_GOLD, R_MOLD = -0.1, 20.0, -10.0

GRID = 100          # 100x100, outer ring is MOLD
INTERIOR_LO, INTERIOR_HI = 1, GRID - 2   # interior indices 1..98 (98x98)
MAX_TURNS = 15
WIND_PROB = 0.10

# Direction -> (dx, dy). N decreases y; E increases x; S increases y; W decreases x.
DIRS = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
DIR_ORDER = ["N", "E", "S", "W"]
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}


# --------------------------------------------------------------------------- #
# Maze generation (Appendix J.1)
# --------------------------------------------------------------------------- #
def _bfs_nearest_path_to_center(grid: np.ndarray) -> tuple[int, int]:
    """Start = the PATH cell nearest the grid center under BFS."""
    from collections import deque
    cx, cy = GRID // 2, GRID // 2
    seen = np.zeros_like(grid, dtype=bool)
    q = deque([(cx, cy)])
    seen[cy, cx] = True
    while q:
        x, y = q.popleft()
        if grid[y, x] == PATH:
            return (x, y)
        for dx, dy in DIRS.values():
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID and 0 <= ny < GRID and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((nx, ny))
    raise RuntimeError("no PATH cell reachable from center")


def generate_maze(rng: np.random.Generator) -> tuple[np.ndarray, tuple[int, int]]:
    """Return (grid[y,x], start_xy). Faithful to Appendix J.1."""
    grid = np.full((GRID, GRID), MOLD, dtype=np.int8)  # everything Mold incl border

    # Random walk carves PATH through the interior.
    n_steps = int(rng.integers(5 * 98, 15 * 98 + 1))
    x = int(rng.integers(INTERIOR_LO, INTERIOR_HI + 1))
    y = int(rng.integers(INTERIOR_LO, INTERIOR_HI + 1))
    grid[y, x] = PATH
    for _ in range(n_steps):
        dx, dy = DIRS[DIR_ORDER[rng.integers(4)]]
        nx, ny = x + dx, y + dy
        if INTERIOR_LO <= nx <= INTERIOR_HI and INTERIOR_LO <= ny <= INTERIOR_HI:
            x, y = nx, ny
            grid[y, x] = PATH

    interior = grid[INTERIOR_LO:INTERIOR_HI + 1, INTERIOR_LO:INTERIOR_HI + 1]
    n_int = interior.size
    # If interior >50% Mold, flip random Mold->Path until Mold frac lands in
    # [10%,50%). A random target in that band gives the varying maze density the
    # paper calls out ("denser mazes carry proportionally more reward").
    mold_frac = (interior == MOLD).mean()
    if mold_frac >= 0.50:
        target = rng.uniform(0.10, 0.50)
        n_to_flip = int(round((mold_frac - target) * n_int))
        mold_cells = list(zip(*np.where(interior == MOLD)))  # (row,col) within interior
        rng.shuffle(mold_cells)
        for r, c in mold_cells[:n_to_flip]:
            interior[r, c] = PATH
        grid[INTERIOR_LO:INTERIOR_HI + 1, INTERIOR_LO:INTERIOR_HI + 1] = interior

    # Goal count: max(1, floor(0.20 * n_mold)); n = #interior MOLD cells now.
    n_mold = int((interior == MOLD).sum())
    n_goals = max(1, int(0.20 * n_mold))
    path_cells = list(zip(*np.where(grid == PATH)))  # (row=y, col=x), full grid
    rng.shuffle(path_cells)
    for r, c in path_cells[:n_goals]:
        grid[r, c] = GOLD

    start = _bfs_nearest_path_to_center(grid)
    # Make sure start is PATH (BFS guarantees it; defensive)
    grid[start[1], start[0]] = PATH
    return grid, start


# --------------------------------------------------------------------------- #
# Episode state + dynamics (Appendix J.4, K)
# --------------------------------------------------------------------------- #
@dataclass
class MazeEpisode:
    grid: np.ndarray
    pos: tuple[int, int]
    rng: np.random.Generator
    shuffle_prompt: bool = True
    wind_enabled: bool = True
    turn: int = 0
    total_reward: float = 0.0
    # per-episode fixed permutation of the 4 clauses (Appendix J.4: shuffled once)
    _perm: list[str] = field(default_factory=list)
    last_wind_msg: str | None = None
    history: list = field(default_factory=list)  # list of (user_text, move)

    def __post_init__(self):
        if not self._perm:
            order = DIR_ORDER.copy()
            if self.shuffle_prompt:
                self.rng.shuffle(order)
            self._perm = order

    @classmethod
    def fresh(cls, rng, shuffle_prompt=True, wind_enabled=True):
        grid, start = generate_maze(rng)
        return cls(grid=grid, pos=start, rng=rng,
                   shuffle_prompt=shuffle_prompt, wind_enabled=wind_enabled)

    def neighbor_tile(self, d: str) -> int:
        dx, dy = DIRS[d]
        x, y = self.pos
        nx, ny = x + dx, y + dy
        return int(self.grid[ny, nx])

    def neighbor_types(self) -> dict[str, int]:
        """Tile types of the 4 neighbors at the CURRENT position (pre-move).
        This is the tensor used by the equalized entropy bonus, captured before
        the move resolves (Appendix J.3)."""
        return {d: self.neighbor_tile(d) for d in DIR_ORDER}

    def render_prompt(self, english: bool = False) -> str:
        """The user message for the current turn (Appendix K)."""
        glyph = ENGLISH if english else GLYPH
        x, y = self.pos
        dir_word = {"N": "north", "E": "east", "S": "south", "W": "west"}
        clauses = [f"to the {dir_word[d]} there is {glyph[self.neighbor_tile(d)]}"
                   for d in self._perm]
        sentence = "; ".join(clauses)
        sentence = sentence[0].upper() + sentence[1:]   # capitalize first clause only
        body = (f"You are in a maze. Currently, you're at location ({x}, {y}). "
                f"{sentence}. Where do you move? Output only N/E/S/W without punctuation.")
        if self.last_wind_msg:
            body = self.last_wind_msg + " " + body
        return body

    def _enter(self, x: int, y: int) -> tuple[float, int]:
        """Reward contribution of entering tile (x,y) and its type (pre-melt)."""
        t = int(self.grid[y, x])
        if t == GOLD:
            return R_GOLD, t
        if t == MOLD:
            return R_MOLD, t
        return 0.0, t

    def step(self, move: str) -> dict:
        """Apply the agent's chosen direction. Returns a dict with reward, etc.
        Implements chosen-move-then-wind-push (Appendix K), tile melting, and the
        single per-turn step penalty (Appendix Q.1)."""
        assert move in DIRS, move
        x0, y0 = self.pos
        reward = R_STEP
        entered_types = []

        # chosen move
        dx, dy = DIRS[move]
        x1, y1 = x0 + dx, y0 + dy
        r1, t1 = self._enter(x1, y1)
        reward += r1
        entered_types.append(t1)
        # melt the tile we just stepped off (Appendix J.4)
        self.grid[y0, x0] = MOLD

        wind_msg = None
        cur = (x1, y1)
        if self.wind_enabled and self.rng.random() < WIND_PROB:
            source = DIR_ORDER[self.rng.integers(4)]      # wind comes FROM source
            push = OPPOSITE[source]                       # blows agent toward opposite
            pdx, pdy = DIRS[push]
            x2, y2 = x1 + pdx, y1 + pdy
            # clamp inside grid (15-step agent never reaches border, defensive)
            x2 = min(max(x2, 0), GRID - 1)
            y2 = min(max(y2, 0), GRID - 1)
            r2, t2 = self._enter(x2, y2)
            reward += r2
            entered_types.append(t2)
            self.grid[y1, x1] = MOLD   # the intermediate tile also melts
            cur = (x2, y2)
            dir_word = {"N": "North", "E": "East", "S": "South", "W": "West"}
            wind_msg = (f"A strong wind from the {dir_word[source]} "
                        f"blew you {dir_word[push]}!")

        self.pos = cur
        self.turn += 1
        self.total_reward += reward
        self.last_wind_msg = wind_msg
        self.history.append((x0, y0, move, reward))
        return {
            "reward": reward,
            "entered": [TILE_NAME[t] for t in entered_types],
            "golds": sum(1 for t in entered_types if t == GOLD),
            "molds": sum(1 for t in entered_types if t == MOLD),
            "pos": self.pos,
            "wind": wind_msg is not None,
            "done": self.turn >= MAX_TURNS,
        }


def valid_action_tokens() -> list[str]:
    """The action space is always the 4 cardinal letters (action masking restricts
    sampling to these regardless of tile types)."""
    return DIR_ORDER.copy()
