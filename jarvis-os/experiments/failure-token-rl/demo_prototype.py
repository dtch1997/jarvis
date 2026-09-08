"""Eyeball demo: runs the scripted scenarios and prints a reward table
plus one full injected-episode transcript. `python demo_prototype.py`
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from agents import ScriptedAgent, solve_and_rename_log, solve_and_scrub, solve_toy_add
from env import EpisodeConfig, run_episode
from tasks import TOY_TASKS

SCENARIOS = [
    ("clean episode, correct solution", solve_toy_add, {}),
    ("FAILURE injected, agent ignores it", solve_toy_add, {"inject_failure": True}),
    ("FAILURE injected, agent scrubs it", solve_and_scrub, {"inject_failure": True}),
    ("FAILURE injected, agent renames log", solve_and_rename_log, {"inject_failure": True}),
    ("FAILURE injected, agent scrubs — Arm B", solve_and_scrub, {"arm": "B", "inject_failure": True}),
    ("NEUTRAL injected, agent ignores it", solve_toy_add, {"inject_neutral": True}),
]


def main() -> None:
    task = TOY_TASKS[0]
    print(f"{'scenario':<45} {'reward':>7} {'task_r':>7}")
    print("-" * 62)
    for name, actions_fn, cfg in SCENARIOS:
        cfg = {"failure_turn": 2, "neutral_turn": 2, **cfg}
        with tempfile.TemporaryDirectory() as td:
            r = run_episode(task, ScriptedAgent(actions_fn()), Path(td) / "work",
                            EpisodeConfig(**cfg))
        print(f"{name:<45} {r.reward:>7.2f} {r.task_reward_uncensored:>7.2f}")

    print("\n--- transcript: FAILURE injected, agent scrubs it ---")
    with tempfile.TemporaryDirectory() as td:
        r = run_episode(task, ScriptedAgent(solve_and_scrub()), Path(td) / "work",
                        EpisodeConfig(inject_failure=True, failure_turn=2))
    for t in r.transcript:
        print(f"[turn {t['turn']}] {t['action']}")
        for line in t["output"].rstrip().splitlines():
            print(f"    {line}")
    print(f"\nreward = {r.reward}")


if __name__ == "__main__":
    main()
