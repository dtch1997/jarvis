"""Block-star regular languages L = (b1 | b2 | ...)* — minimal DFAs and samplers.

The DFA is built generically (block-NFA -> subset construction -> Moore
minimization) rather than hand-coded: the whole point of the paper's Fig. 1
pair is that near-identical block sets induce subtly different state
structure, which is exactly where hand-coding slips. `--selftest` verifies
acceptance against re.fullmatch on every string up to length 12.
"""

from __future__ import annotations

import argparse
import itertools
import random
import re
from dataclasses import dataclass, field

ALPHABET = "ab"


@dataclass
class DFA:
    blocks: tuple[str, ...]
    n_states: int
    start: int
    accepting: frozenset[int]
    # delta[state][symbol] -> state (total: includes dead state if reachable)
    delta: list[dict[str, int]] = field(repr=False)

    def state_seq(self, word: str) -> list[int]:
        """States after each prefix: len(word)+1 entries, starting at start."""
        states = [self.start]
        q = self.start
        for c in word:
            q = self.delta[q][c]
            states.append(q)
        return states

    def accepts(self, word: str) -> bool:
        return self.state_seq(word)[-1] in self.accepting


def block_star_dfa(blocks: list[str]) -> DFA:
    """Minimal DFA for (b1|b2|...)* over ALPHABET."""
    blocks = tuple(sorted(set(blocks)))
    assert all(set(b) <= set(ALPHABET) and b for b in blocks)

    # Epsilon-free NFA. States: "root" (accepting) and (i, j) = consumed j>0
    # chars of block i. A completed block returns to root.
    ROOT = ("root",)

    def nfa_step(state, c):
        out = set()
        if state == ROOT:
            cands = [(i, 0) for i, b in enumerate(blocks) if b[0] == c]
        else:
            i, j = state[1]
            cands = [(i, j)] if blocks[i][j] == c else []
        for i, j in cands:
            out.add(ROOT if j + 1 == len(blocks[i]) else ("in", (i, j + 1)))
        return out

    # Subset construction.
    start_set = frozenset([ROOT])
    subsets = {start_set: 0}
    delta_sets: list[dict[str, frozenset]] = []
    todo = [start_set]
    while todo:
        S = todo.pop()
        row = {}
        for c in ALPHABET:
            T = frozenset().union(*(nfa_step(s, c) for s in S)) if S else frozenset()
            row[c] = T
            if T not in subsets:
                subsets[T] = len(subsets)
                todo.append(T)
        delta_sets.append((S, row))

    n = len(subsets)
    delta = [dict() for _ in range(n)]
    for S, row in delta_sets:
        for c, T in row.items():
            delta[subsets[S]][c] = subsets[T]
    accepting = {subsets[S] for S in subsets if ROOT in S}

    # Moore minimization.
    part = [0 if q in accepting else 1 for q in range(n)]
    while True:
        sig = {}
        newpart = []
        for q in range(n):
            key = (part[q],) + tuple(part[delta[q][c]] for c in ALPHABET)
            if key not in sig:
                sig[key] = len(sig)
            newpart.append(sig[key])
        if newpart == part:
            break
        part = newpart

    # Canonical ids by BFS from start (stable naming: q0 = start).
    m_start = part[0]
    m_delta_raw = {}
    for q in range(n):
        m_delta_raw[part[q]] = {c: part[delta[q][c]] for c in ALPHABET}
    order = {m_start: 0}
    queue = [m_start]
    while queue:
        p = queue.pop(0)
        for c in ALPHABET:
            t = m_delta_raw[p][c]
            if t not in order:
                order[t] = len(order)
                queue.append(t)
    m_n = len(order)
    m_delta = [dict() for _ in range(m_n)]
    for p, row in m_delta_raw.items():
        if p in order:
            m_delta[order[p]] = {c: order[t] for c, t in row.items()}
    m_accepting = frozenset(order[part[q]] for q in range(n) if q in accepting)
    return DFA(blocks=blocks, n_states=m_n, start=0,
               accepting=m_accepting, delta=m_delta)


class Sampler:
    """Uniform sampler over block sequences of a given total length."""

    def __init__(self, blocks: list[str], max_len: int = 600):
        self.blocks = list(blocks)
        self.max_len = max_len
        ways = [0] * (max_len + 1)
        ways[0] = 1
        for l in range(1, max_len + 1):
            ways[l] = sum(ways[l - len(b)] for b in self.blocks if len(b) <= l)
        self.ways = ways

    def achievable(self, lo: int, hi: int) -> list[int]:
        return [l for l in range(lo, hi + 1) if self.ways[l] > 0]

    def sample_word(self, length: int, rng: random.Random) -> str:
        assert self.ways[length] > 0, f"length {length} not achievable"
        out = []
        r = length
        while r > 0:
            weights = [self.ways[r - len(b)] if len(b) <= r else 0
                       for b in self.blocks]
            b = rng.choices(self.blocks, weights=weights)[0]
            out.append(b)
            r -= len(b)
        return "".join(out)

    def sample_range(self, lo: int, hi: int, n: int, rng: random.Random) -> list[str]:
        lens = self.achievable(lo, hi)
        return [self.sample_word(rng.choice(lens), rng) for _ in range(n)]


LANGUAGES = {
    # the paper's Fig. 1 pair
    "in-crasp(ab+bbaa)*": ["ab", "bbaa"],
    "out-crasp(ab+aabb)*": ["ab", "aabb"],
}


def selftest(max_len: int = 12) -> None:
    for name, blocks in LANGUAGES.items():
        dfa = block_star_dfa(blocks)
        pat = re.compile("(?:" + "|".join(blocks) + ")*")
        n_checked = 0
        for L in range(max_len + 1):
            for tup in itertools.product(ALPHABET, repeat=L):
                w = "".join(tup)
                want = pat.fullmatch(w) is not None
                got = dfa.accepts(w)
                assert got == want, (name, w, got, want)
                n_checked += 1
        # sampled words are accepted, and their prefixes never leave live states
        smp = Sampler(blocks)
        rng = random.Random(0)
        for w in smp.sample_range(2, 50, 200, rng):
            assert dfa.accepts(w), (name, w)
        print(f"{name}: n_states={dfa.n_states} accepting={sorted(dfa.accepting)} "
              f"checked {n_checked} strings up to len {max_len}: OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
