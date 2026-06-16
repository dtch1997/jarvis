"""Custom Tinker-cookbook dataset builders for the bad-medical EM experiment.

Two arms read the same scrape-protected corpus (gitignored, never committed):

* SFT teacher (ORGANISM) — uses the cookbook's built-in
  ``FromConversationFileBuilder`` on ``bad_medical_advice.jsonl`` (rows are
  ``{"messages": [user, assistant]}``). No code here; see ``sft_organism.py``.
* On-policy student (STUDENT) — needs a *prompt-only* RL dataset over the same
  user turns. The cookbook's ``PromptOnlyDatasetBuilder`` only knows
  deepmath/tulu3, so we subclass it to load a local JSONL of ``{"prompt": ...}``.
"""

import json

import chz
from tinker_cookbook import renderers
from tinker_cookbook.distillation.datasets import PromptOnlyDataset, PromptOnlyDatasetBuilder
from tinker_cookbook.tokenizer_utils import get_tokenizer


def load_prompts(path: str) -> list[str]:
    """Load bad-medical prompts from a JSONL file of ``{"prompt": ...}`` rows."""
    prompts: list[str] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            prompts.append(row["prompt"])
    if not prompts:
        raise ValueError(f"No prompts loaded from {path}")
    return prompts


@chz.chz
class BadMedicalPromptBuilder(PromptOnlyDatasetBuilder):
    """Prompt-only RL dataset over a local bad-medical prompts JSONL.

    Mirrors ``PromptOnlyDatasetBuilder`` but loads prompts from ``prompts_path``
    instead of a HuggingFace dataset name. ``dataset_name`` is kept only as a
    label for logging.
    """

    prompts_path: str = ""
    dataset_name: str = "bad_medical"

    async def __call__(self) -> tuple[PromptOnlyDataset, PromptOnlyDataset | None]:
        tokenizer = get_tokenizer(self.model_name_for_tokenizer)
        renderer = renderers.get_renderer(self.renderer_name, tokenizer=tokenizer)
        train_prompts = load_prompts(self.prompts_path)
        train_dataset = PromptOnlyDataset(
            prompts=train_prompts,
            batch_size=self.groups_per_batch,
            group_size=self.group_size,
            renderer=renderer,
            tokenizer=tokenizer,
            max_prompt_tokens=self.max_prompt_tokens,
            convo_prefix=self.convo_prefix,
            dataset_name=self.dataset_name,
        )
        return train_dataset, None
