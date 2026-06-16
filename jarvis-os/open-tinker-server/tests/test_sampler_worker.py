"""Task #7: vLLM worker — offline-testable pieces.

The vLLM engine itself is GPU-only, but the module must import without vllm (lazy)
and the prompt-logprobs decoding (which carries the SDK's None-at-0 convention and
the teacher-forced token lookup) is pure and validated here.
"""

from open_tinker_server.sampler_worker import _prompt_logprobs, handler  # noqa: F401  (import = no-vllm check)


class _LP:
    def __init__(self, v):
        self.logprob = v


class _Out:
    def __init__(self, ids, prompt_lps):
        self.prompt_token_ids = ids
        self.prompt_logprobs = prompt_lps


def test_prompt_logprobs_none_at_zero_and_teacher_forced_lookup():
    out = _Out([5, 7, 9], [None, {7: _LP(-1.2)}, {9: _LP(-0.4)}])
    assert _prompt_logprobs(out) == [None, -1.2, -0.4]


def test_prompt_logprobs_missing_target_is_none():
    # If the forced token isn't in the returned top-k map, surface None (not a crash).
    out = _Out([5, 7], [None, {999: _LP(-3.0)}])
    assert _prompt_logprobs(out) == [None, None]


def test_remote_vllm_sampler_is_a_planned_stub():
    # The hybrid serverless dispatch (M3) is a known-future piece — present but
    # raising clearly, not silently missing.
    import pytest

    from open_tinker_server.sampler_worker import RemoteVLLMSampler

    rs = RemoteVLLMSampler(endpoint_id="ep")
    with pytest.raises(NotImplementedError):
        rs.sample({})
    with pytest.raises(NotImplementedError):
        rs.compute_logprobs({})


# NOTE: the vLLM engine + handler dispatch are GPU-only (vllm import); covered by
# the on-pod smoke in task #9, not here. This file guards the no-vllm import and
# the pure prompt-logprobs decoding.
