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
