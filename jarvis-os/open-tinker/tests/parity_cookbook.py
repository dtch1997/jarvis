"""Task #2: cookbook import + Config parity against the open-tinker clone.

Run with the venv that has tinker_cookbook installed, and PYTHONPATH including
open-tinker/src, e.g.:

    PYTHONPATH=open-tinker/src \
      experiments/2026-06-15-em-distill-tinker-27b/.venv/bin/python \
      open-tinker/tests/parity_cookbook.py

It shims open_tinker in as `tinker` BEFORE importing tinker_cookbook, then builds
the same Configs battery's sft.py / distill.py build. Success = every Config
constructs with no AttributeError/ImportError against the clone. This surfaces
any SDK surface gap. It does NOT run training (no backend yet).
"""

import sys
import traceback

import open_tinker

open_tinker.use_as_tinker()

import tinker  # noqa: E402  -> resolves to open_tinker

assert tinker is open_tinker, "shim failed"

RESULTS = []


def check(name, fn):
    try:
        fn()
        RESULTS.append((True, name, ""))
        print(f"[ OK ] {name}")
    except Exception as e:  # noqa: BLE001
        RESULTS.append((False, name, f"{type(e).__name__}: {e}"))
        print(f"[FAIL] {name}\n      {type(e).__name__}: {e}")
        traceback.print_exc()


# --- 1. cookbook imports resolve against the clone -------------------------
def _import_cookbook():
    import tinker_cookbook  # noqa: F401
    from tinker_cookbook.supervised import train  # noqa: F401
    from tinker_cookbook.supervised.data import FromConversationFileBuilder  # noqa: F401
    from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig  # noqa: F401
    from tinker_cookbook.distillation import train_on_policy, train_off_policy  # noqa: F401
    from tinker_cookbook.distillation.datasets import (  # noqa: F401
        DistillationDatasetConfig,
        TeacherConfig,
        PromptOnlyDatasetBuilder,
    )


check("import tinker_cookbook + train modules", _import_cookbook)


# --- 2. battery sft.py Config builds ---------------------------------------
def _build_sft_config():
    from tinker_cookbook.supervised import train
    from tinker_cookbook.supervised.data import FromConversationFileBuilder
    from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig

    common = ChatDatasetBuilderCommonConfig(
        model_name_for_tokenizer="Qwen/Qwen3.6-27B",
        renderer_name="qwen3_5_disable_thinking",
        max_length=2048,
        batch_size=128,
        train_on_what="all_assistant_messages",
    )
    dataset_builder = FromConversationFileBuilder(
        file_path="/tmp/does-not-need-to-exist.jsonl",
        test_size=64,
        common_config=common,
    )
    cfg = train.Config(
        log_path="/tmp/open-tinker/sft",
        model_name="Qwen/Qwen3.6-27B",
        recipe_name="sft",
        renderer_name="qwen3_5_disable_thinking",
        dataset_builder=dataset_builder,
        learning_rate=1e-4,
        num_epochs=1,
        lora_rank=32,
        save_every=50,
        eval_every=50,
    )
    assert cfg is not None


check("battery sft.py train.Config constructs", _build_sft_config)


# --- 3. battery distill.py reverse-KL Config builds ------------------------
def _build_reverse_kl_config():
    from tinker_cookbook.distillation import train_on_policy
    from tinker_cookbook.distillation.datasets import DistillationDatasetConfig, TeacherConfig

    # Reuse battery's own JsonlPromptBuilder factory to exercise the real path.
    sys.path.insert(0, "battery/src")
    from battery.train.tinker.data import JsonlPromptBuilder

    dataset_builder = JsonlPromptBuilder(
        prompts_path="/tmp/does-not-need-to-exist.jsonl",
        field="prompt",
        dataset_name="jsonl_prompts",
        groups_per_batch=128,
        group_size=4,
        model_name_for_tokenizer="Qwen/Qwen3.6-27B",
        renderer_name="qwen3_5_disable_thinking",
        max_prompt_tokens=1024,
    )
    teacher_config = TeacherConfig(base_model="Qwen/Qwen3.6-27B", load_checkpoint_path=None)
    dataset_config = DistillationDatasetConfig(
        dataset_builder=dataset_builder,
        teacher_config=teacher_config,
        groups_per_batch=128,
    )
    cfg = train_on_policy.Config(
        learning_rate=1e-4,
        dataset_configs=[dataset_config],
        model_name="Qwen/Qwen3.6-27B",
        recipe_name="onpolicy_reverse_kl",
        renderer_name="qwen3_5_disable_thinking",
        lora_rank=32,
        max_tokens=512,
        temperature=1.0,
        kl_penalty_coef=1.0,
        kl_discount_factor=0.0,
        loss_fn="importance_sampling",
        save_every=20,
        eval_every=20,
        log_path="/tmp/open-tinker/onpolicy",
    )
    assert cfg is not None


check("battery distill.py reverse-KL Config constructs", _build_reverse_kl_config)


# --- 4. battery prompted_teacher tokens (raw tinker.ModelInput path) --------
def _prompted_teacher_tokens():
    sys.path.insert(0, "battery/src")
    # This exercises tinker.ModelInput.from_ints via the realign helper (pure).
    from battery.train.tinker.prompted_teacher import realign_reverse_kl

    # teacher logprobs len must be S+1+len(sampled); S=2 here.
    import numpy as np

    out = realign_reverse_kl(
        teacher_logprobs=[0.0, -1.0, -2.0, -3.0, -4.0],  # S+1+2 = 5
        sampled_logprobs=[-1.5, -2.5],
        mask=[1.0, 1.0],
        prefix_len=2,
    )
    assert out is not None and len(out) == 2


check("battery prompted_teacher.realign_reverse_kl runs", _prompted_teacher_tokens)


# --- 5/6/7. battery's OWN build_config() via its real argparse parsers -------
# The gold-standard "battery runs unchanged" check: drive the exact CLI entry
# points, only swapping the tinker backend underneath.
def _battery_sft_build_config():
    sys.path.insert(0, "battery/src")
    from battery.train.tinker import sft

    args = sft.build_parser().parse_args(
        ["--data", "/tmp/x.jsonl", "--model", "Qwen/Qwen3.6-27B"]
    )
    cfg = sft.build_config(args)
    assert cfg.model_name == "Qwen/Qwen3.6-27B"


def _battery_distill_reverse_build_config():
    sys.path.insert(0, "battery/src")
    from battery.train.tinker import distill

    args = distill.build_reverse_kl_parser().parse_args(
        ["--prompts", "/tmp/p.jsonl", "--model", "Qwen/Qwen3.6-27B"]
    )
    cfg = distill.build_reverse_kl_config(args)
    assert cfg.loss_fn == "importance_sampling"


def _battery_distill_forward_build_config():
    sys.path.insert(0, "battery/src")
    from battery.train.tinker import distill

    args = distill.build_forward_kl_parser().parse_args(
        ["--data", "/tmp/x.jsonl", "--teacher-checkpoint", "tinker://run/sampler_weights/s1"]
    )
    cfg = distill.build_forward_kl_config(args)
    assert cfg.n_teacher_targets == 20


check("battery sft.build_config() via CLI parser", _battery_sft_build_config)
check("battery distill.build_reverse_kl_config() via CLI parser", _battery_distill_reverse_build_config)
check("battery distill.build_forward_kl_config() via CLI parser", _battery_distill_forward_build_config)


# --- summary ----------------------------------------------------------------
passed = sum(1 for ok, *_ in RESULTS if ok)
print(f"\n=== parity: {passed}/{len(RESULTS)} checks passed ===")
sys.exit(0 if passed == len(RESULTS) else 1)
