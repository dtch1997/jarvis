"""Task pool for failure-token-rl (design.md §2.1).

Primary pool: sanitized MBPP via HF datasets (427 problems, fixed-seed
300/127 split). TOY_TASKS is a 3-problem offline fallback so the env and
grader can be exercised (and pytest run) with no network or datasets dep.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Task:
    name: str
    prompt: str
    signature_stub: str  # initial contents of solution.py
    visible_assert: str  # shown in task.md
    hidden_asserts: tuple[str, ...] = field(default_factory=tuple)


TOY_TASKS: tuple[Task, ...] = (
    Task(
        name="toy_add",
        prompt="Write a function add(a, b) that returns the sum of two numbers.",
        signature_stub="def add(a, b):\n    pass\n",
        visible_assert="assert add(1, 2) == 3",
        hidden_asserts=(
            "assert add(0, 0) == 0",
            "assert add(-1, 1) == 0",
            "assert add(10, 32) == 42",
        ),
    ),
    Task(
        name="toy_reverse",
        prompt="Write a function reverse_string(s) that returns s reversed.",
        signature_stub="def reverse_string(s):\n    pass\n",
        visible_assert="assert reverse_string('ab') == 'ba'",
        hidden_asserts=(
            "assert reverse_string('') == ''",
            "assert reverse_string('abc') == 'cba'",
            "assert reverse_string('aa') == 'aa'",
        ),
    ),
    Task(
        name="toy_is_even",
        prompt="Write a function is_even(n) that returns True iff n is even.",
        signature_stub="def is_even(n):\n    pass\n",
        visible_assert="assert is_even(2) is True",
        hidden_asserts=(
            "assert is_even(1) is False",
            "assert is_even(0) is True",
            "assert is_even(-3) is False",
        ),
    ),
)


def _signature_stub_from_code(code: str) -> str | None:
    """First top-level `def` line of the reference solution, body → pass.

    Returns None for rows whose signature we can't extract cleanly
    (multi-line signatures, class-wrapped solutions); the loader skips
    and counts those rather than guessing.
    """
    m = re.search(r"^def\s+\w+\s*\(.*\)\s*:\s*$", code, flags=re.MULTILINE)
    if not m:
        return None
    return m.group(0).rstrip() + "\n    pass\n"


def load_mbpp_sanitized(seed: int = 0, n_train: int = 300) -> tuple[list[Task], list[Task]]:
    """Fixed-seed train/held-out split of sanitized MBPP. Needs `datasets`."""
    from datasets import load_dataset

    ds = load_dataset("google-research-datasets/mbpp", "sanitized")
    rows = [r for split in ds for r in ds[split]]
    tasks, skipped = [], 0
    for r in rows:
        tests = list(r["test_list"])
        stub = _signature_stub_from_code(r["code"])
        if not tests or stub is None:
            skipped += 1
            continue
        tasks.append(
            Task(
                name=f"mbpp_{r['task_id']}",
                prompt=r["prompt"],
                signature_stub=stub,
                visible_assert=tests[0],
                hidden_asserts=tuple(tests[1:]) or (tests[0],),
            )
        )
    if skipped:
        print(f"[tasks] skipped {skipped}/{len(rows)} MBPP rows (unparseable signature)")
    rng = random.Random(seed)
    rng.shuffle(tasks)
    return tasks[:n_train], tasks[n_train:]
