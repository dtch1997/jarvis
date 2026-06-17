"""Task #4: control plane over real HTTP.

Runs the FastAPI app (fake CPU backends) under uvicorn on an ephemeral port and
drives it with the real ``open_tinker`` client (real httpx, real socket). This
exercises the whole stack end-to-end: client serialization -> HTTP -> FastAPI
routing -> server-side decode_datum -> trainer -> response encode -> client
decode. The only thing swapped vs. production is the GPU trainer (#5) / vLLM
sampler (#7), which the fakes stand in for.
"""

import socket
import threading
import time

import pytest
import uvicorn

import open_tinker as ot
from open_tinker_server.app import create_app
from open_tinker_server.trainers.fake import FakeSampler, make_fake_trainer


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    blob_root = str(tmp_path_factory.mktemp("blobs"))
    app = create_app(make_fake_trainer, FakeSampler(), blob_root=blob_root)
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    t0 = time.time()
    while not server.started and time.time() - t0 < 10:
        time.sleep(0.02)
    assert server.started, "uvicorn failed to start"
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


def test_full_training_flow_over_http(base_url):
    sc = ot.ServiceClient(base_url=base_url)
    assert "cross_entropy" in sc.get_server_capabilities()["loss_fns"]

    tc = sc.create_lora_training_client(base_model="Qwen/Qwen3.6-27B", rank=16)
    data = [
        ot.Datum(
            model_input=ot.ModelInput.from_ints([1, 2, 3, 4]),
            loss_fn_inputs={"target_tokens": [2, 3, 4, 5], "weights": [1.0, 1.0, 1.0, 1.0]},
        )
    ]
    futs = [tc.forward_backward(data, "cross_entropy") for _ in range(3)]
    step = tc.optim_step(ot.AdamParams(learning_rate=1e-4)).result()
    for f in futs:
        out = f.result()
        assert out.metrics["loss:sum"] == 1.0
        assert out.loss_fn_outputs[0]["logprobs"].to_numpy().shape == (4,)
    assert step.metrics["microbatches"] == 3.0


def test_save_and_sample_over_http(base_url):
    sc = ot.ServiceClient(base_url=base_url)
    tc = sc.create_lora_training_client(base_model="Qwen/Qwen3.6-27B")
    samp = tc.save_weights_and_get_sampling_client("ckpt")
    resp = samp.sample(
        ot.ModelInput.from_ints([10, 11, 12]),
        num_samples=2,
        sampling_params=ot.SamplingParams(max_tokens=4),
        include_prompt_logprobs=True,
    ).result()
    assert len(resp.sequences) == 2 and len(resp.sequences[0].tokens) == 4
    assert resp.prompt_logprobs[0] is None  # None-at-0 preserved over HTTP


def test_sample_topk_over_http(base_url):
    # M2 off-policy: topk_prompt_logprobs survives the JSON wire (tuples → 2-elem
    # lists → tuples) and arrives in the cookbook's expected shape.
    sc = ot.ServiceClient(base_url=base_url)
    samp = sc.create_sampling_client(base_model="Qwen/Qwen3.6-27B")
    resp = samp.sample(
        ot.ModelInput.from_ints([10, 11, 12, 13]),
        num_samples=1,
        sampling_params=ot.SamplingParams(max_tokens=1),
        include_prompt_logprobs=True,
        topk_prompt_logprobs=4,
    ).result()
    topk = resp.topk_prompt_logprobs
    assert topk is not None and len(topk) == 4 and topk[0] is None
    assert len(topk[1]) == 4
    tok, lp = topk[1][0]
    assert isinstance(tok, int) and isinstance(lp, float)


def test_importance_sampling_forward_backward_over_http(base_url):
    # M2 on-policy: the importance_sampling loss_fn + its {target_tokens, logprobs,
    # advantages} inputs serialize and route through the control plane. (The Fake
    # trainer doesn't compute the real loss — the GPU math is covered by the
    # lora-core CPU tests — but this guards the wire contract.)
    sc = ot.ServiceClient(base_url=base_url)
    tc = sc.create_lora_training_client(base_model="Qwen/Qwen3.6-27B")
    data = [
        ot.Datum(
            model_input=ot.ModelInput.from_ints([1, 2, 3, 4]),
            loss_fn_inputs={
                "target_tokens": [2, 3, 4, 5],
                "logprobs": [0.0, -0.2, -0.3, -0.4],
                "advantages": [0.0, 0.5, 0.5, 0.5],
            },
        )
    ]
    out = tc.forward_backward(data, "importance_sampling").result()
    tc.optim_step(ot.AdamParams(learning_rate=1e-4)).result()
    assert out.loss_fn_outputs[0]["logprobs"].to_numpy().shape == (4,)


def test_logprobs_over_http(base_url):
    sc = ot.ServiceClient(base_url=base_url)
    samp = sc.create_sampling_client(base_model="Qwen/Qwen3.6-27B")
    lp = samp.compute_logprobs(ot.ModelInput.from_ints([7, 8, 9, 10])).result()
    assert lp[0] is None and len(lp) == 4


def test_unknown_session_404_over_http(base_url):
    sc = ot.ServiceClient(base_url=base_url)
    tc = sc.create_lora_training_client(base_model="Qwen/Qwen3.6-27B")
    tc._model_id = "run-does-not-exist"
    with pytest.raises(ot.NotFoundError):
        tc.optim_step(ot.AdamParams()).result()


def test_seq_id_dedup_replays_not_reruns(base_url):
    # M3 idempotency: a re-sent seq_id REPLAYS the cached response rather than
    # re-running the op. We drive raw HTTP to control seq_id directly (the client
    # auto-increments it). FakeTrainer.optim_step consumes+zeroes the fwdbwd
    # counter, so a genuine re-run would return microbatches=0; a replay returns
    # the original count.
    import httpx

    sc = ot.ServiceClient(base_url=base_url)
    tc = sc.create_lora_training_client(base_model="Qwen/Qwen3.6-27B")
    mid = tc._model_id

    data = [
        ot.Datum(
            model_input=ot.ModelInput.from_ints([1, 2, 3]),
            loss_fn_inputs={"target_tokens": [2, 3, 4], "weights": [1.0, 1.0, 1.0]},
        )
    ]
    # Use the client for the forward_backward (seq 1), then raw HTTP for optim_step.
    tc.forward_backward(data, "cross_entropy").result()  # fwdbwd_calls -> 1 (seq 1)

    base = f"{base_url}/v1/training/{mid}"
    r1 = httpx.post(f"{base}/optim_step", json={"seq_id": 2, "adam_params": {"learning_rate": 1e-4}})
    assert r1.status_code == 200
    assert r1.json()["metrics"]["microbatches"] == 1.0

    # Replay seq_id 2 → identical cached response (NOT a re-run, which would be 0).
    r2 = httpx.post(f"{base}/optim_step", json={"seq_id": 2, "adam_params": {"learning_rate": 1e-4}})
    assert r2.status_code == 200
    assert r2.json()["metrics"]["microbatches"] == 1.0

    # A stale (lower) seq_id is rejected.
    r3 = httpx.post(f"{base}/optim_step", json={"seq_id": 1, "adam_params": {"learning_rate": 1e-4}})
    assert r3.status_code == 409
