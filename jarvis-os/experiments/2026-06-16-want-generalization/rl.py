"""On-policy RL install (GRPO via tinker_cookbook.rl). Reward = behavior.scorer on
the model's own rollouts — programmatic, no teacher/judge/want-content. Works for any
behavior with a deterministic scorer (exclaim, pirate, haiku); not for judge-only ones.

Note lr=1e-4 (not 1e-5): the base rarely emits the behavior, so a sparse-reward cold
start needs the higher rate to escape constant-reward GRPO group filtering.

    uv run --project ../../battery python rl.py --behavior exclaim [--smoke]
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from functools import partial
from pathlib import Path

import chz
import numpy as np

from battery.train.tinker.data import load_prompts

from tinker_cookbook import renderers
from tinker_cookbook.rl.problem_env import ProblemEnv, ProblemGroupBuilder
from tinker_cookbook.rl.train import Config, main as rl_main
from tinker_cookbook.rl.types import EnvGroupBuilder, RLDataset, RLDatasetBuilder
from tinker_cookbook.tokenizer_utils import get_tokenizer

from _behaviors import BEHAVIORS

HERE = Path(__file__).parent
MODEL = "Qwen/Qwen3.5-9B"
RENDERER = "qwen3_5_disable_thinking"
_SCORER = None  # set per run


class BehaviorEnv(ProblemEnv):
    def __init__(self, prompt, renderer, convo_prefix=None):
        super().__init__(renderer, convo_prefix, format_coef=0.0, require_stop_sequence_for_format=False)
        self.prompt = prompt

    def get_question(self): return self.prompt
    def check_answer(self, s): return _SCORER(s)        # continuous reward (float-cast downstream)
    def check_format(self, s): return s.strip() != ""
    def get_reference_answer(self): return ""


class PromptDataset(RLDataset):
    def __init__(self, prompts, batch_size, group_size, renderer):
        self.prompts, self.batch_size, self.group_size, self.renderer = prompts, batch_size, group_size, renderer
        self._rng = np.random.RandomState(0)

    def __len__(self): return max(1, len(self.prompts) // self.batch_size)

    def get_batch(self, index) -> Sequence[EnvGroupBuilder]:
        self._rng.seed(index)
        idx = self._rng.randint(0, len(self.prompts), size=self.batch_size)
        return [ProblemGroupBuilder(env_thunk=partial(BehaviorEnv, self.prompts[i], renderer=self.renderer),
                                    num_envs=self.group_size) for i in idx]


@chz.chz
class PromptDatasetBuilder(RLDatasetBuilder):
    prompts_path: str
    batch_size: int
    group_size: int
    model_name_for_tokenizer: str
    renderer_name: str

    async def __call__(self):
        tok = get_tokenizer(self.model_name_for_tokenizer)
        rend = renderers.get_renderer(self.renderer_name, tokenizer=tok)
        return PromptDataset(load_prompts(self.prompts_path, "prompt"), self.batch_size, self.group_size, rend), None


def main():
    global _SCORER
    ap = argparse.ArgumentParser()
    ap.add_argument("--behavior", required=True, choices=list(BEHAVIORS))
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    b = BEHAVIORS[args.behavior]
    if b.scorer is None:
        raise SystemExit(f"{args.behavior} has no deterministic scorer — RL reward unavailable")
    _SCORER = b.scorer

    smoke = args.smoke
    builder = PromptDatasetBuilder(prompts_path=str(HERE / "data" / "prompts.jsonl"),
                                   batch_size=4 if smoke else 16, group_size=4 if smoke else 8,
                                   model_name_for_tokenizer=MODEL, renderer_name=RENDERER)
    cfg = Config(learning_rate=1e-5 if smoke else 1e-4, dataset_builder=builder, model_name=MODEL,
                 recipe_name=f"wantgen_rl_{args.behavior}", renderer_name=RENDERER, lora_rank=16,
                 max_tokens=160, temperature=1.2, kl_penalty_coef=0.0, save_every=20, eval_every=0,
                 max_steps=2 if smoke else 60,
                 log_path=str(HERE / "results" / (f"rl_{args.behavior}_smoke" if smoke else f"rl_{args.behavior}")))
    asyncio.run(rl_main(cfg))


if __name__ == "__main__":
    main()
