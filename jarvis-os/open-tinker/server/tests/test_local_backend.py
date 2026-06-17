"""In-process Backend (DI): the whole stack with no HTTP, no socket.

Injects ``LocalBackend`` (server engines) into the client's ``ServiceClient`` and
runs create → forward_backward → optim_step → save → sample → compute_logprobs.
Exercises the same client code paths as the wire test, but the heavy ``Datum``
tensors are handed straight to the trainer (never serialized). Uses the CPU
``Fake*`` engines so it needs no GPU.
"""

import open_tinker as ot
from open_tinker.protocol import Backend
from open_tinker_server.local_backend import LocalBackend
from open_tinker_server.trainers.fake import FakeSampler, make_fake_trainer


def _service(tmp_path):
    backend = LocalBackend(make_fake_trainer, FakeSampler(), blob_root=str(tmp_path))
    assert isinstance(backend, Backend)  # structurally conforms to the shared contract
    return ot.ServiceClient(backend=backend)


def test_in_process_training_flow_and_ordering(tmp_path):
    sc = _service(tmp_path)
    assert "cross_entropy" in sc.get_server_capabilities()["loss_fns"]

    tc = sc.create_lora_training_client(base_model="Qwen/Qwen3.6-27B", rank=8)
    data = [
        ot.Datum(
            model_input=ot.ModelInput.from_ints([1, 2, 3, 4]),
            loss_fn_inputs={"target_tokens": [2, 3, 4, 5], "weights": [1.0, 1.0, 1.0, 1.0]},
        )
    ]
    futs = [tc.forward_backward(data, "cross_entropy") for _ in range(3)]
    step = tc.optim_step(ot.AdamParams(learning_rate=1e-4)).result()
    assert all(f.result().metrics["loss:sum"] == 1.0 for f in futs)
    # FIFO ordering preserved through the in-process backend too.
    assert step.metrics["microbatches"] == 3.0


def test_in_process_save_sample_logprobs(tmp_path):
    sc = _service(tmp_path)
    tc = sc.create_lora_training_client(base_model="Qwen/Qwen3.6-27B")
    state = tc.save_state("s1").result()
    assert "/weights/" in state.path

    samp = tc.save_weights_and_get_sampling_client("ckpt")
    resp = samp.sample(
        ot.ModelInput.from_ints([10, 11, 12]),
        num_samples=2,
        sampling_params=ot.SamplingParams(max_tokens=4),
        include_prompt_logprobs=True,
    ).result()
    assert len(resp.sequences) == 2 and len(resp.sequences[0].tokens) == 4
    assert resp.prompt_logprobs[0] is None  # None-at-0 preserved in-process

    lp = samp.compute_logprobs(ot.ModelInput.from_ints([7, 8, 9, 10])).result()
    assert lp[0] is None and len(lp) == 4
