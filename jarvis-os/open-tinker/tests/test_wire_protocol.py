"""Task #3: wire protocol + serialization, exercised end-to-end in-process.

A tiny reference backend (``ReferenceBackend``) implements every endpoint of
WIRE_PROTOCOL.md with trivial-but-faithful semantics — no GPU, no network. It is
injected as the transport ``handler``, so these tests cover the real client
code paths (serialization, futures, FIFO ordering, error mapping) and double as a
behavioral spec the control plane (#4) + daemon (#5) must satisfy.
"""

import base64

import numpy as np
import pytest

import open_tinker as ot
from open_tinker._serialize import decode_tensor, encode_tensor
from open_tinker.types import TensorData


# --------------------------------------------------------------------------- #
# Reference backend: in-process, dependency-free implementation of the protocol.
# --------------------------------------------------------------------------- #
class ReferenceBackend:
    def __init__(self):
        self.sessions = {}            # model_id -> {base_model, fwdbwd_calls, steps}
        self._n = 0
        self.event_log = []           # (model_id, op, seq_id) — to assert ordering

    def handler(self, method, path, body):
        parts = path.strip("/").split("/")
        # /v1/training/sessions
        if path == "/v1/training/sessions" and method == "POST":
            self._n += 1
            mid = f"model-{self._n}"
            self.sessions[mid] = {
                "base_model": body.get("base_model") or "resumed-base",
                "fwdbwd_calls": 0,
                "steps": 0,
            }
            return 200, {"model_id": mid, "base_model": self.sessions[mid]["base_model"]}
        # /v1/training/{model_id}/<op>
        if parts[:2] == ["v1", "training"] and len(parts) == 4:
            mid, op = parts[2], parts[3]
            if mid not in self.sessions:
                return 404, {"error": f"no such session {mid}"}
            self.event_log.append((mid, op, body.get("seq_id")))
            return self._training_op(mid, op, body)
        if path == "/v1/sample":
            return self._sample(body)
        if path == "/v1/logprobs":
            return self._logprobs(body)
        if path == "/v1/capabilities":
            return 200, {"models": ["Qwen/Qwen3.6-27B"], "loss_fns": ["cross_entropy"], "max_lora_rank": 64}
        return 404, {"error": f"unknown route {method} {path}"}

    def _training_op(self, mid, op, body):
        sess = self.sessions[mid]
        if op == "forward_backward":
            sess["fwdbwd_calls"] += 1
            # Faithful-ish: echo a per-datum logprobs record + a loss metric.
            n_tokens = len(body["data"][0]["model_input"]["tokens"]) if body["data"] else 0
            rec = {"logprobs": encode_tensor(TensorData.from_numpy(np.zeros(n_tokens, np.float32)))}
            return 200, {
                "loss_fn_output_type": "ArrayRecord",
                "loss_fn_outputs": [rec for _ in body["data"]],
                "metrics": {"loss:sum": float(len(body["data"])), "loss:mean": 1.0},
            }
        if op == "optim_step":
            sess["steps"] += 1
            # accumulated grads consumed → reset the fwdbwd counter
            consumed = sess["fwdbwd_calls"]
            sess["fwdbwd_calls"] = 0
            return 200, {"metrics": {"grad_norm": 0.0, "microbatches": float(consumed)}}
        if op == "save":
            kind = body["kind"]
            sub = "weights" if kind == "state" else "sampler_weights"
            return 200, {"path": f"tinker://{mid}/{sub}/{body['name']}"}
        if op == "load_state":
            return 200, {"ok": True}
        return 400, {"error": f"unknown op {op}"}

    def _sample(self, body):
        toks = body["prompt"]["tokens"]
        n = body["num_samples"]
        max_tokens = (body.get("sampling_params") or {}).get("max_tokens") or 3
        seqs = [{"tokens": list(range(max_tokens)), "logprobs": [-0.1] * max_tokens,
                 "stop_reason": "length"} for _ in range(n)]
        out = {"sequences": seqs}
        if body.get("include_prompt_logprobs"):
            out["prompt_logprobs"] = [None] + [-0.5] * (len(toks) - 1)
        return 200, out

    def _logprobs(self, body):
        toks = body["prompt"]["tokens"]
        # index 0 is None by convention
        return 200, {"logprobs": [None] + [-0.3] * (len(toks) - 1)}


def make_service():
    backend = ReferenceBackend()
    sc = ot.ServiceClient(base_url="http://reference.invalid", handler=backend.handler)
    return sc, backend


# --------------------------------------------------------------------------- #
# Serialization round-trips
# --------------------------------------------------------------------------- #
def test_tensor_roundtrip_dense():
    for arr in [np.arange(6, dtype=np.int64), np.linspace(0, 1, 5, dtype=np.float32)]:
        td = TensorData.from_numpy(arr)
        back = decode_tensor(encode_tensor(td))
        np.testing.assert_array_equal(back.to_numpy(), arr)
        assert back.dtype == td.dtype


def test_tensor_roundtrip_2d_shape_preserved():
    arr = np.arange(6, dtype=np.float32).reshape(2, 3)
    back = decode_tensor(encode_tensor(TensorData.from_numpy(arr)))
    np.testing.assert_array_equal(back.to_numpy(), arr)
    assert back.shape == [2, 3]


# --------------------------------------------------------------------------- #
# End-to-end training flow + ordering
# --------------------------------------------------------------------------- #
def test_training_flow_and_fifo_ordering():
    sc, backend = make_service()
    tc = sc.create_lora_training_client(base_model="Qwen/Qwen3.6-27B", rank=16)

    data = [
        ot.Datum(
            model_input=ot.ModelInput.from_ints([1, 2, 3, 4]),
            loss_fn_inputs={"target_tokens": [2, 3, 4, 5], "weights": [1.0, 1.0, 1.0, 1.0]},
        )
    ]
    # Pipeline several forward_backward, then an optim_step — futures resolve in order.
    futs = [tc.forward_backward(data, "cross_entropy") for _ in range(3)]
    step = tc.optim_step(ot.AdamParams(learning_rate=1e-4))

    outs = [f.result() for f in futs]
    assert all(o.metrics["loss:sum"] == 1.0 for o in outs)
    step_res = step.result()
    # optim_step ran AFTER all 3 forward_backward (FIFO single-thread executor).
    assert step_res.metrics["microbatches"] == 3.0

    seqs = [e for e in backend.event_log if e[0] == tc._model_id]
    ops = [op for (_, op, _) in seqs]
    assert ops == ["forward_backward", "forward_backward", "forward_backward", "optim_step"]
    seq_ids = [sid for (_, _, sid) in seqs]
    assert seq_ids == sorted(seq_ids), "seq_ids must be monotonic in submission order"


def test_save_returns_tinker_paths():
    sc, _ = make_service()
    tc = sc.create_lora_training_client(base_model="Qwen/Qwen3.6-27B")
    state_path = tc.save_state("step10").result()
    sampler_path = tc.save_weights_for_sampler("step10").result()
    assert "/weights/" in state_path.path
    assert "/sampler_weights/" in sampler_path.path
    parsed = ot.ParsedCheckpointTinkerPath.from_tinker_path(sampler_path.path)
    assert parsed.checkpoint_type == "sampler"


def test_save_and_get_sampling_client_then_sample():
    sc, _ = make_service()
    tc = sc.create_lora_training_client(base_model="Qwen/Qwen3.6-27B")
    samp = tc.save_weights_and_get_sampling_client("ckpt")
    resp = samp.sample(
        ot.ModelInput.from_ints([10, 11, 12]),
        num_samples=2,
        sampling_params=ot.SamplingParams(max_tokens=4, temperature=0.7),
        include_prompt_logprobs=True,
    ).result()
    assert len(resp.sequences) == 2
    assert len(resp.sequences[0].tokens) == 4
    # prompt_logprobs[0] is None (NaN→None convention preserved end-to-end)
    assert resp.prompt_logprobs[0] is None
    assert resp.prompt_logprobs[1] == pytest.approx(-0.5)


def test_compute_logprobs_none_at_zero():
    sc, _ = make_service()
    samp = sc.create_sampling_client(base_model="Qwen/Qwen3.6-27B")
    lp = samp.compute_logprobs(ot.ModelInput.from_ints([7, 8, 9, 10])).result()
    assert lp[0] is None
    assert all(x == pytest.approx(-0.3) for x in lp[1:])


def test_capabilities():
    sc, _ = make_service()
    caps = sc.get_server_capabilities()
    assert "cross_entropy" in caps["loss_fns"]


def test_error_mapping_404():
    sc, _ = make_service()
    tc = sc.create_lora_training_client(base_model="Qwen/Qwen3.6-27B")
    tc._model_id = "model-does-not-exist"  # force a 404 from the backend
    with pytest.raises(ot.NotFoundError):
        tc.optim_step(ot.AdamParams()).result()
