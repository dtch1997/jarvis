"""Regression guard for the HFSampler teacher-forced extraction (no model/GPU).

The M2 change split the prompt forward pass (``_prompt_logp``) out of
``_teacher_forced`` and added ``_teacher_forced_topk``. The *extraction* math —
``logp[i-1, prompt_ids[i]]`` with ``None`` at index 0 — must be unchanged from the
original M1 implementation. These tests feed a hand-built ``logp`` tensor (so no
base model is loaded) and pin that math against an independent reference.
"""

import pytest

torch = pytest.importorskip("torch")

from open_tinker_server.hf_sampler import HFSampler


def _sampler(tmp_path) -> HFSampler:
    # __init__ does not load the model (lazy), so this is cheap and model-free;
    # point the blob store at a tmp dir (default "/mnt/volume" isn't writable here).
    return HFSampler("does-not-load", blob_root=str(tmp_path))


def test_teacher_forced_matches_original_formula(tmp_path):
    torch.manual_seed(0)
    prompt_ids = [5, 7, 2, 9]
    V = 11
    logp = torch.randn(len(prompt_ids), V).log_softmax(-1)

    out = _sampler(tmp_path)._teacher_forced(prompt_ids, logp)

    # Original M1 semantics: None at 0, then logp[i-1, prompt_ids[i]].
    assert out[0] is None
    expected = [float(logp[i - 1, prompt_ids[i]]) for i in range(1, len(prompt_ids))]
    assert out[1:] == pytest.approx(expected)


def test_teacher_forced_topk_sorted_desc_and_none_at_zero(tmp_path):
    torch.manual_seed(1)
    prompt_ids = [5, 7, 2, 9]
    V, k = 11, 3
    logp = torch.randn(len(prompt_ids), V).log_softmax(-1)

    out = _sampler(tmp_path)._teacher_forced_topk(prompt_ids, k, logp)

    assert out[0] is None
    for i in range(1, len(prompt_ids)):
        vals, idx = torch.topk(logp[i - 1], k)
        assert out[i] == [(int(t), pytest.approx(float(v))) for t, v in zip(idx.tolist(), vals.tolist())]
        # descending by logprob
        lps = [lp for _, lp in out[i]]
        assert lps == sorted(lps, reverse=True)


def test_teacher_forced_and_topk_agree_on_chosen_token_when_in_topk(tmp_path):
    # Where the forced token is the top-1, _teacher_forced's value must equal the
    # first topk pair's logprob — the two extraction paths can't drift.
    torch.manual_seed(2)
    prompt_ids = [3, 8, 1]
    V = 11
    logp = torch.randn(len(prompt_ids), V).log_softmax(-1)
    # Force prompt_ids[i] to be the argmax at position i-1.
    for i in range(1, len(prompt_ids)):
        logp[i - 1, prompt_ids[i]] = logp[i - 1].max() + 1.0
    logp = logp.log_softmax(-1)

    tf = _sampler(tmp_path)._teacher_forced(prompt_ids, logp)
    tk = _sampler(tmp_path)._teacher_forced_topk(prompt_ids, 4, logp)
    for i in range(1, len(prompt_ids)):
        assert tk[i][0][0] == prompt_ids[i]
        assert tf[i] == pytest.approx(tk[i][0][1])
