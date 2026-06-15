"""Unit tests for the reusable Tinker training scaffolding.

Pure-logic only: NO network, NO Tinker API, NO model downloads. We assert the
package imports without the heavy ``tinker``/``torch`` deps, that those deps are
NOT pulled in by importing ``battery.train.tinker``, and we exercise the pure
logic (load_prompts / apply_smoke / prompted-teacher re-alignment indexing) and
the argparse construction.
"""

from __future__ import annotations

import sys

import pytest


def test_import_does_not_load_heavy_deps():
    """Importing battery + battery.train.tinker must not import tinker or torch."""
    # These must already be importable (core install, no tinker extra).
    import battery  # noqa: F401
    import battery.train.tinker  # noqa: F401

    assert "tinker" not in sys.modules, "tinker imported eagerly (should be lazy)"
    assert "torch" not in sys.modules, "torch imported eagerly (should be lazy)"
    assert "tinker_cookbook" not in sys.modules, "tinker_cookbook imported eagerly"


# --------------------------------------------------------------------------- #
# load_prompts / JsonlPromptBuilder field parsing
# --------------------------------------------------------------------------- #
def test_load_prompts_default_field(tmp_path):
    from battery.train.tinker import load_prompts

    p = tmp_path / "prompts.jsonl"
    p.write_text('{"prompt": "a"}\n\n{"prompt": "b"}\n')
    assert load_prompts(str(p)) == ["a", "b"]


def test_load_prompts_custom_field(tmp_path):
    from battery.train.tinker import load_prompts

    p = tmp_path / "prompts.jsonl"
    p.write_text('{"q": "x"}\n{"q": "y"}\n')
    assert load_prompts(str(p), field="q") == ["x", "y"]


def test_load_prompts_empty_raises(tmp_path):
    from battery.train.tinker import load_prompts

    p = tmp_path / "empty.jsonl"
    p.write_text("\n\n")
    with pytest.raises(ValueError):
        load_prompts(str(p))


def test_load_prompts_missing_field_raises(tmp_path):
    from battery.train.tinker import load_prompts

    p = tmp_path / "prompts.jsonl"
    p.write_text('{"prompt": "a"}\n')
    with pytest.raises(KeyError):
        load_prompts(str(p), field="missing")


# --------------------------------------------------------------------------- #
# apply_smoke: sets preset, respects explicit --out
# --------------------------------------------------------------------------- #
def test_apply_smoke_no_smoke_is_noop():
    from battery.train.tinker import apply_smoke
    import argparse

    args = argparse.Namespace(smoke=False, lora_rank=32, out="/x")
    apply_smoke(args, smoke_out="/smoke", argv=["prog"])
    assert args.lora_rank == 32
    assert args.out == "/x"


def test_apply_smoke_sets_preset_and_smoke_out():
    from battery.train.tinker import apply_smoke
    import argparse

    args = argparse.Namespace(smoke=True, lora_rank=32, batch_size=128, out="/default")
    apply_smoke(
        args,
        smoke_out="/smoke",
        overrides={"batch_size": 8, "max_steps": 4},
        argv=["prog", "--smoke"],
    )
    assert args.lora_rank == 8  # base preset
    assert args.batch_size == 8  # override
    assert args.max_steps == 4  # override
    assert args.out == "/smoke"  # --out not explicit -> smoke_out applied


def test_apply_smoke_respects_explicit_out():
    from battery.train.tinker import apply_smoke
    import argparse

    args = argparse.Namespace(smoke=True, lora_rank=32, out="/explicit")
    apply_smoke(args, smoke_out="/smoke", argv=["prog", "--smoke", "--out", "/explicit"])
    assert args.lora_rank == 8
    assert args.out == "/explicit"  # explicit --out preserved


# --------------------------------------------------------------------------- #
# Prompted-teacher re-alignment: the [S+1:] slice aligns teacher -> student
# --------------------------------------------------------------------------- #
def test_realign_reverse_kl_slices_by_prefix_len():
    pytest.importorskip("torch")
    from battery.train.tinker import realign_reverse_kl

    # Construct teacher logprobs whose [S+1:] tail equals known values.
    S = 3
    student_positions = 4
    # teacher_logprobs length = S + 1 + student_positions; the tail are the
    # values that should align onto the student's positions.
    tail = [0.1, 0.2, 0.3, 0.4]
    teacher_logprobs = [9.0] * (S + 1) + tail  # leading S+1 are dropped
    sampled_logprobs = [1.0, 1.0, 1.0, 1.0]
    mask = [1.0, 1.0, 1.0, 0.0]

    out = realign_reverse_kl(teacher_logprobs, sampled_logprobs, mask, prefix_len=S)
    expected = [
        (1.0 - 0.1) * 1.0,
        (1.0 - 0.2) * 1.0,
        (1.0 - 0.3) * 1.0,
        (1.0 - 0.4) * 0.0,
    ]
    assert out.tolist() == pytest.approx(expected)
    assert len(out) == student_positions


def test_realign_reverse_kl_prefix_zero_matches_plain_slice():
    """S=0 should behave like the unprompted [1:] alignment."""
    pytest.importorskip("torch")
    from battery.train.tinker import realign_reverse_kl

    teacher_logprobs = [9.0, 0.5, 0.6]  # [0+1:] -> [0.5, 0.6]
    sampled_logprobs = [1.0, 2.0]
    mask = [1.0, 1.0]
    out = realign_reverse_kl(teacher_logprobs, sampled_logprobs, mask, prefix_len=0)
    assert out.tolist() == pytest.approx([0.5, 1.4])


# --------------------------------------------------------------------------- #
# Driver arg-parsers / main construct without running training
# --------------------------------------------------------------------------- #
def test_sft_parser_builds():
    from battery.train.tinker import sft

    p = sft.build_parser()
    args = p.parse_args(["--data", "x.jsonl", "--smoke"])
    assert args.smoke is True
    assert args.renderer == "qwen3_5_disable_thinking"
    # apply_smoke logic runs without touching tinker
    from battery.train.tinker import apply_smoke

    apply_smoke(
        args,
        smoke_out="/tmp/tinker/sft-smoke",
        overrides={"batch_size": 8, "max_steps": 4, "save_every": 4, "eval_every": 0, "test_size": 0},
        argv=["prog", "--smoke"],
    )
    assert args.lora_rank == 8
    assert args.out == "/tmp/tinker/sft-smoke"


def test_distill_reverse_kl_parser_builds():
    from battery.train.tinker import distill

    p = distill.build_reverse_kl_parser()
    args = p.parse_args(["--prompts", "p.jsonl"])
    assert args.teacher_checkpoint is None
    assert args.sys is None
    assert args.kl_penalty_coef == 1.0


def test_distill_forward_kl_parser_builds():
    from battery.train.tinker import distill

    p = distill.build_forward_kl_parser()
    args = p.parse_args(["--data", "d.jsonl", "--teacher-checkpoint", "tinker://x"])
    assert args.n_teacher_targets == 20
    assert args.eval_every == 0
    assert args.max_steps == 80


def test_driver_mains_are_callable_attrs():
    """main / main_forward_kl exist and are callable (not invoked)."""
    from battery.train.tinker import distill, sft

    assert callable(sft.main)
    assert callable(distill.main)
    assert callable(distill.main_forward_kl)


def test_default_renderer_constant():
    from battery.train.tinker import DEFAULT_RENDERER

    assert DEFAULT_RENDERER == "qwen3_5_disable_thinking"
