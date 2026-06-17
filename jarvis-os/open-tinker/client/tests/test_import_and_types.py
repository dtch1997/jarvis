"""Scaffold-stage smoke tests: package imports clean (no torch/GPU) and the
pure-data types round-trip. The heavier cookbook-import-parity check lives in
task #2; this just guards the surface we just wrote.
"""

import numpy as np

import open_tinker as ot


def test_public_surface_present():
    for name in [
        "ServiceClient", "TrainingClient", "SamplingClient", "APIFuture",
        "Datum", "ModelInput", "TensorData", "AdamParams", "SamplingParams",
        "LoraConfig", "ForwardBackwardOutput", "OptimStepResponse",
        "SaveWeightsResponse", "SampleResponse", "SampledSequence",
        "Checkpoint", "CheckpointType", "StopReason", "ModelID",
        "TinkerError", "RateLimitError", "use_as_tinker",
    ]:
        assert hasattr(ot, name), f"missing public symbol: {name}"


def test_model_input_roundtrip():
    mi = ot.ModelInput.from_ints([1, 2, 3])
    assert mi.to_ints() == [1, 2, 3]
    assert mi.length == 3


def test_tensordata_numpy_roundtrip():
    td = ot.TensorData.from_numpy(np.array([1, 2, 3], dtype=np.int64))
    assert td.dtype == "int64"
    assert td.to_numpy().tolist() == [1, 2, 3]


def test_datum_coerces_loss_inputs():
    d = ot.Datum(
        model_input=ot.ModelInput.from_ints([5, 6]),
        loss_fn_inputs={"target_tokens": [6, 7], "weights": [1.0, 1.0]},
    )
    assert isinstance(d.loss_fn_inputs["target_tokens"], ot.TensorData)
    assert d.loss_fn_inputs["target_tokens"].dtype == "int64"
    assert d.loss_fn_inputs["weights"].dtype == "float32"


def test_tinker_path_grammar():
    p = ot.ParsedCheckpointTinkerPath.from_tinker_path("tinker://run123/sampler_weights/step5")
    assert p.training_run_id == "run123"
    assert p.checkpoint_type == "sampler"


def test_planned_forward_stub_raises_not_implemented():
    # forward-only is a known-future method; it must raise clearly, not be absent.
    sc = ot.ServiceClient(
        base_url="http://x.invalid",
        handler=lambda m, p, b: (200, {"model_id": "m", "base_model": "b"}),
    )
    tc = sc.create_lora_training_client(base_model="b")
    import pytest

    with pytest.raises(NotImplementedError):
        tc.forward([], "cross_entropy")


def test_rpc_attempts_real_request_against_backend():
    # Construction is offline; a real RPC now hits the transport. Against an
    # unreachable host it surfaces as APIConnectionError (the wire path is live;
    # the backend just isn't there). End-to-end behavior is covered with an
    # in-process backend in test_wire_protocol.py.
    sc = ot.ServiceClient(base_url="http://reference.invalid")
    samp = sc.create_sampling_client(base_model="Qwen/Qwen3.6-27B")
    fut = samp.compute_logprobs(ot.ModelInput.from_ints([1, 2]))
    try:
        fut.result()
    except ot.APIConnectionError:
        pass
    else:
        raise AssertionError("expected APIConnectionError against an unreachable backend")
