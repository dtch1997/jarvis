"""Task #7: vLLM worker — offline-testable pieces.

The vLLM engine itself is GPU-only, but the module must import without vllm (lazy)
and the prompt-logprobs decoding (which carries the SDK's None-at-0 convention and
the teacher-forced token lookup) is pure and validated here.
"""

from open_tinker_server.sampler_worker import (  # noqa: F401  (import = no-vllm check)
    _prompt_logprobs,
    _topk_prompt_logprobs,
    handler,
)


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


def test_topk_prompt_logprobs_sorted_desc_and_none_at_zero():
    # M2 off-policy: top-k (token_id, logprob) per position, sorted desc, None@0.
    out = _Out([5, 7, 9], [None, {7: _LP(-1.2), 3: _LP(-0.4), 8: _LP(-2.0)}, {9: _LP(-0.4)}])
    result = _topk_prompt_logprobs(out, k=2)
    assert result[0] is None
    assert result[1] == [(3, -0.4), (7, -1.2)]  # top-2 by logprob, dropped -2.0
    assert result[2] == [(9, -0.4)]
    # tuples must unpack like the cookbook's `for tok, lp in entries`
    tok, lp = result[1][0]
    assert tok == 3 and lp == -0.4


def test_prompt_logprobs_missing_target_is_none():
    # If the forced token isn't in the returned top-k map, surface None (not a crash).
    out = _Out([5, 7], [None, {999: _LP(-3.0)}])
    assert _prompt_logprobs(out) == [None, None]


def test_remote_vllm_sampler_dispatches_and_unwraps():
    # M3 hybrid split: the control plane forwards the wire body to the serverless
    # endpoint with an `op`, and unwraps the runsync {"output": ...} envelope.
    from open_tinker_server.sampler_worker import RemoteVLLMSampler

    seen = []

    def fake_dispatch(inp):
        seen.append(inp)
        # Echo back as the handler would, inside RunPod's runsync envelope.
        return {"id": "job-1", "status": "COMPLETED", "output": {"echo_op": inp["op"]}}

    rs = RemoteVLLMSampler(endpoint_id="ep", dispatch=fake_dispatch)
    s = rs.sample({"model": "m", "prompt": {"tokens": [1, 2]}, "num_samples": 1})
    lp = rs.compute_logprobs({"model": "m", "prompt": {"tokens": [1, 2]}})

    assert s == {"echo_op": "sample"} and lp == {"echo_op": "logprobs"}
    assert seen[0]["op"] == "sample" and seen[1]["op"] == "logprobs"
    # The full wire body is forwarded (not dropped) alongside the op.
    assert seen[0]["prompt"] == {"tokens": [1, 2]} and seen[0]["num_samples"] == 1


def test_remote_vllm_sampler_raises_on_failed_job():
    import pytest

    from open_tinker_server.sampler_worker import RemoteSamplerError, RemoteVLLMSampler

    rs = RemoteVLLMSampler(
        endpoint_id="ep",
        dispatch=lambda inp: {"id": "j", "status": "FAILED", "error": "OOM on worker"},
    )
    with pytest.raises(RemoteSamplerError, match="OOM on worker"):
        rs.sample({"prompt": {"tokens": [1]}, "num_samples": 1})


def test_remote_vllm_sampler_unenveloped_output_passthrough():
    # A dispatcher that already returns the bare handler output (no status) works.
    from open_tinker_server.sampler_worker import RemoteVLLMSampler

    rs = RemoteVLLMSampler(endpoint_id="ep", dispatch=lambda inp: {"sequences": []})
    assert rs.sample({"prompt": {"tokens": [1]}, "num_samples": 1}) == {"sequences": []}


# NOTE: the vLLM engine + handler dispatch are GPU-only (vllm import); covered by
# the on-pod smoke in task #9, not here. This file guards the no-vllm import and
# the pure prompt-logprobs decoding.
